"""Servicio de abastecimientos (Fase 6 · recepción de mercadería).

El proveedor es obligatorio en todo abastecimiento normal. La confirmación mueve
existencias, guarda costos por presentación y actualiza el último costo conocido
del vínculo producto–proveedor.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Abastecimiento,
    Almacen,
    DetalleAbastecimiento,
    PresentacionProducto,
    Producto,
    TipoMovimiento,
)
from app.domain.unidades import (
    ErrorNegocio,
    ErrorStockInsuficiente,
    convertir_a_base,
    dec,
    num,
    q2,
    q4,
    q6,
)
from app.services import inventario
from app.services import lotes as servicio_lotes
from app.services.secuencias import siguiente_numero


def _principal(db: Session) -> Almacen:
    almacen = db.execute(
        select(Almacen).where(Almacen.activo.is_(True)).order_by(Almacen.id)
    ).scalars().first()
    if almacen is None:
        raise ErrorNegocio("No hay un almacén activo configurado.")
    return almacen


def _resolver_almacen(db: Session, almacen_id: int | None) -> Almacen:
    if almacen_id is None:
        return _principal(db)
    almacen = db.get(Almacen, almacen_id)
    if almacen is None or not almacen.activo:
        raise ErrorNegocio("El almacén indicado no existe o está inactivo.")
    return almacen


def _cargar_presentacion(
    db: Session, producto_id: int, presentacion_id: int
) -> tuple[Producto, PresentacionProducto]:
    producto = db.execute(
        select(Producto).options(selectinload(Producto.unidad_base)).where(Producto.id == producto_id)
    ).scalar_one_or_none()
    if producto is None:
        raise ErrorNegocio("El producto de la línea no existe.", detalle={"producto_id": producto_id})
    presentacion = db.get(PresentacionProducto, presentacion_id)
    if presentacion is None or presentacion.producto_id != producto.id:
        raise ErrorNegocio(
            "La presentación indicada no corresponde al producto de la línea.",
            detalle={"presentacion_id": presentacion_id},
        )
    if not producto.activo:
        raise ErrorNegocio(
            f"El producto «{producto.nombre}» está desactivado y no puede ingresarse.",
            detalle={"producto_id": producto.id},
        )
    if not presentacion.activo or not presentacion.es_compra:
        raise ErrorNegocio(
            f"La presentación «{presentacion.nombre}» no está disponible para compra.",
            detalle={"presentacion_id": presentacion.id},
        )
    return producto, presentacion


def previsualizar(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    almacen = _resolver_almacen(db, payload.get("almacen_id"))
    lineas: list[dict[str, Any]] = []
    total = Decimal("0")
    alertas_minimo = 0

    for linea in payload["lineas"]:
        producto, presentacion = _cargar_presentacion(
            db, linea["producto_id"], linea["presentacion_id"]
        )
        cantidad = dec(linea["cantidad"])
        conversion = convertir_a_base(
            cantidad,
            dec(presentacion.factor_base),
            producto.unidad_base.paso_minimo if producto.unidad_base else 1,
            permite_fraccion=bool(presentacion.permite_fraccion or producto.permite_fraccion),
        )
        costo = dec(linea["costo_unitario"])
        subtotal = q2(cantidad * costo)

        existencia = inventario.existencia_actual(db, almacen.id, producto.id)
        stock_actual = dec(existencia.cantidad_base) if existencia else Decimal("0")
        stock_minimo = dec(producto.stock_minimo_base)
        resultado = stock_actual + conversion.cantidad_base

        alerta = None
        if stock_minimo > 0 and resultado < stock_minimo:
            alerta = "sigue_bajo_minimo"
            alertas_minimo += 1

        total += subtotal
        lineas.append(
            {
                "producto_id": producto.id,
                "producto_codigo": producto.codigo,
                "producto_nombre": producto.nombre,
                "presentacion_id": presentacion.id,
                "presentacion_nombre": presentacion.nombre,
                "cantidad": num(q4(cantidad)),
                "factor_snapshot": num(presentacion.factor_base),
                "cantidad_base": num(q4(conversion.cantidad_base)),
                "unidad_base": producto.unidad_base.nombre if producto.unidad_base else None,
                "costo_unitario": num(q2(costo)),
                "subtotal": str(subtotal),
                "stock_actual_base": num(q4(stock_actual)),
                "stock_resultante_base": num(q4(resultado)),
                "alerta": alerta,
            }
        )

    return {"total": num(q2(total)), "lineas": lineas, "alertas_stock_minimo": alertas_minimo}


def confirmar(db: Session, payload: dict[str, Any], usuario_id: int) -> Abastecimiento:
    almacen = _resolver_almacen(db, payload.get("almacen_id"))
    proveedor_id = payload["proveedor_id"]
    fecha = payload.get("fecha") or date.today()

    abastecimiento = Abastecimiento(
        numero="PENDIENTE",
        proveedor_id=proveedor_id,
        almacen_id=almacen.id,
        fecha=fecha,
        documento=(payload.get("documento") or "").strip() or None,
        observaciones=payload.get("observaciones"),
        estado="CONFIRMADO",
        usuario_id=usuario_id,
        total=0,
    )
    db.add(abastecimiento)
    db.flush()
    abastecimiento.numero = siguiente_numero(db, "ABASTECIMIENTO", almacen.id)

    total = Decimal("0")

    for linea in payload["lineas"]:
        producto, presentacion = _cargar_presentacion(
            db, linea["producto_id"], linea["presentacion_id"]
        )
        cantidad = dec(linea["cantidad"])
        conversion = convertir_a_base(
            cantidad,
            dec(presentacion.factor_base),
            producto.unidad_base.paso_minimo if producto.unidad_base else 1,
            permite_fraccion=bool(presentacion.permite_fraccion or producto.permite_fraccion),
        )
        costo = dec(linea["costo_unitario"])
        subtotal = q2(cantidad * costo)
        costo_base = q6(costo / dec(presentacion.factor_base))
        precio_venta = (
            dec(linea["precio_venta"])
            if linea.get("precio_venta") is not None
            else dec(presentacion.precio_venta)
        )
        fecha_lote = linea.get("fecha_ingreso") or fecha

        # El detalle se guarda primero para que el lote pueda referenciarlo.
        detalle = DetalleAbastecimiento(
            abastecimiento_id=abastecimiento.id,
            producto_id=producto.id,
            presentacion_id=presentacion.id,
            cantidad=q4(cantidad),
            factor_snapshot=dec(presentacion.factor_base),
            cantidad_base=q4(conversion.cantidad_base),
            costo_unitario=q2(costo),
            costo_base=costo_base,
            subtotal=subtotal,
        )
        db.add(detalle)
        db.flush()

        # Cada línea de ingreso crea un LOTE con su costo y su precio de venta.
        # Los lotes anteriores no se tocan.
        lote = servicio_lotes.crear_lote(
            db,
            producto_id=producto.id,
            almacen_id=almacen.id,
            cantidad_base=conversion.cantidad_base,
            cantidad_inicial=conversion.cantidad_base,
            costo_base=costo_base,
            costo_unitario=costo,
            precio_venta=precio_venta,
            presentacion_id=presentacion.id,
            fecha_ingreso=fecha_lote,
            abastecimiento_id=abastecimiento.id,
            detalle_abastecimiento_id=detalle.id,
            usuario_id=usuario_id,
            origen="RECEPCION",
        )
        detalle.lote_id = lote.id

        inventario.aplicar_entrada(
            db,
            almacen_id=almacen.id,
            producto_id=producto.id,
            cantidad_base=conversion.cantidad_base,
            costo_unitario_base=costo_base,
            tipo=TipoMovimiento.ABASTECIMIENTO,
            origen_tipo="ABASTECIMIENTO",
            origen_id=abastecimiento.id,
            usuario_id=usuario_id,
            referencia=abastecimiento.numero,
            lote_id=lote.id,
        )
        total += subtotal

    abastecimiento.total = q2(total)
    db.flush()
    return abastecimiento


def anular(db: Session, abastecimiento_id: int, motivo: str, usuario_id: int) -> Abastecimiento:
    """Revierte un abastecimiento confirmado (nunca lo borra)."""
    abastecimiento = db.execute(
        select(Abastecimiento)
        .options(selectinload(Abastecimiento.detalles))
        .where(Abastecimiento.id == abastecimiento_id)
    ).scalar_one_or_none()
    if abastecimiento is None:
        raise ErrorNegocio("El abastecimiento no existe.", detalle={"abastecimiento_id": abastecimiento_id})
    if abastecimiento.estado != "CONFIRMADO":
        raise ErrorNegocio(
            "El abastecimiento ya fue revertido o no está confirmado.",
            detalle={"estado": abastecimiento.estado.value},
        )

    for detalle in abastecimiento.detalles:
        existencia = inventario.bloquear_existencia(db, abastecimiento.almacen_id, detalle.producto_id)
        stock_actual = dec(existencia.cantidad_base)
        if stock_actual < dec(detalle.cantidad_base):
            raise ErrorStockInsuficiente(
                "No se puede revertir: parte de la mercadería ya fue vendida.",
                detalle={
                    "producto_id": detalle.producto_id,
                    "cantidad_a_retirar": num(q4(dec(detalle.cantidad_base))),
                    "saldo_disponible": num(q4(stock_actual)),
                },
            )
        inventario.aplicar_salida(
            db,
            almacen_id=abastecimiento.almacen_id,
            producto_id=detalle.producto_id,
            cantidad_base=dec(detalle.cantidad_base),
            tipo=TipoMovimiento.REVERSO_ABASTECIMIENTO,
            origen_tipo="ABASTECIMIENTO",
            origen_id=abastecimiento.id,
            usuario_id=usuario_id,
            referencia=abastecimiento.numero,
            lote_id=detalle.lote_id,
        )

    abastecimiento.estado = "REVERTIDO"
    abastecimiento.anulado_por_id = usuario_id
    abastecimiento.anulado_at = datetime.now(timezone.utc)
    abastecimiento.motivo_anulacion = motivo
    db.flush()
    return abastecimiento


def abastecimiento_a_dict(abastecimiento: Abastecimiento) -> dict[str, Any]:
    detalles = []
    for d in abastecimiento.detalles:
        producto = d.producto
        presentacion = d.presentacion
        lote = d.lote
        detalles.append(
            {
                "id": d.id,
                "producto_id": d.producto_id,
                "presentacion_id": d.presentacion_id,
                "cantidad": num(q4(dec(d.cantidad))),
                "factor_snapshot": num(d.factor_snapshot),
                "cantidad_base": num(q4(dec(d.cantidad_base))),
                "costo_unitario": num(q2(dec(d.costo_unitario))),
                "subtotal": num(q2(dec(d.subtotal))),
                "lote_id": d.lote_id,
                "lote_codigo": lote.codigo_lote if lote is not None else None,
                "producto_codigo": producto.codigo if producto else None,
                "producto_nombre": producto.nombre if producto else None,
                "presentacion_nombre": presentacion.nombre if presentacion else None,
            }
        )
    return {
        "id": abastecimiento.id,
        "numero": abastecimiento.numero,
        "proveedor_id": abastecimiento.proveedor_id,
        "proveedor_nombre": abastecimiento.proveedor.razon_social if abastecimiento.proveedor else None,
        "almacen_id": abastecimiento.almacen_id,
        "fecha": abastecimiento.fecha,
        "documento": abastecimiento.documento,
        "observaciones": abastecimiento.observaciones,
        "estado": abastecimiento.estado.value,
        "total": num(q2(dec(abastecimiento.total))),
        "usuario": abastecimiento.usuario.nombre if abastecimiento.usuario else None,
        "created_at": abastecimiento.created_at,
        "detalles": detalles,
    }


__all__ = ["abastecimiento_a_dict", "anular", "confirmar", "previsualizar"]

