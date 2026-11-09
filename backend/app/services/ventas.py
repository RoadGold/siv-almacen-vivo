"""Servicio de ventas (Fase 7 Â· punto de venta).

Reglas clave:
- El servidor recalcula precios, conversiones y disponibilidad: nunca confÃ­a en el total del navegador.
- La confirmaciÃ³n es idempotente: la misma `idempotency_key` devuelve la misma venta.
- Venta + detalles + movimientos + existencias ocurren en una Ãºnica transacciÃ³n.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Almacen,
    DetalleVenta,
    PresentacionProducto,
    Producto,
    TipoMovimiento,
    Venta,
)
from app.domain.unidades import ErrorNegocio, ErrorStockInsuficiente, convertir_a_base, dec, num, q2, q4
from app.services import inventario
from app.services.secuencias import siguiente_numero


def _principal(db: Session) -> Almacen:
    almacen = db.execute(
        select(Almacen).where(Almacen.activo.is_(True)).order_by(Almacen.id)
    ).scalars().first()
    if almacen is None:
        raise ErrorNegocio("No hay un almacÃ©n activo configurado.")
    return almacen


def _resolver_almacen(db: Session, almacen_id: int | None) -> Almacen:
    if almacen_id is None:
        return _principal(db)
    almacen = db.get(Almacen, almacen_id)
    if almacen is None or not almacen.activo:
        raise ErrorNegocio("El almacÃ©n indicado no existe o estÃ¡ inactivo.")
    return almacen


def _cargar_presentacion(
    db: Session, producto_id: int, presentacion_id: int
) -> tuple[Producto, PresentacionProducto]:
    producto = db.execute(
        select(Producto).options(selectinload(Producto.unidad_base)).where(Producto.id == producto_id)
    ).scalar_one_or_none()
    if producto is None:
        raise ErrorNegocio("El producto de la lÃ­nea no existe.", detalle={"producto_id": producto_id})
    presentacion = db.get(PresentacionProducto, presentacion_id)
    if presentacion is None or presentacion.producto_id != producto.id:
        raise ErrorNegocio(
            "La presentaciÃ³n indicada no corresponde al producto de la lÃ­nea.",
            detalle={"presentacion_id": presentacion_id},
        )
    if not producto.activo:
        raise ErrorNegocio(
            f"El producto Â«{producto.nombre}Â» estÃ¡ desactivado y no puede venderse.",
            detalle={"producto_id": producto.id},
        )
    if not presentacion.activo or not presentacion.es_venta:
        raise ErrorNegocio(
            f"La presentaciÃ³n Â«{presentacion.nombre}Â» no estÃ¡ disponible para venta.",
            detalle={"presentacion_id": presentacion.id},
        )
    return producto, presentacion


def previsualizar(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """Calcula el total y la cinta de impacto sin tocar existencias."""
    almacen = _resolver_almacen(db, payload.get("almacen_id"))
    lineas: list[dict[str, Any]] = []
    total = Decimal("0")
    costo_estimado = Decimal("0")
    alertas: list[str] = []

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
        precio = (
            dec(linea["precio_unitario"])
            if linea.get("precio_unitario") is not None
            else dec(presentacion.precio_venta)
        )
        subtotal = q2(cantidad * precio)

        existencia = inventario.existencia_actual(db, almacen.id, producto.id)
        stock_actual = dec(existencia.cantidad_base) if existencia else Decimal("0")
        costo_base = dec(existencia.costo_promedio_base) if existencia else Decimal("0")
        resultado = stock_actual - conversion.cantidad_base

        alerta = None
        if resultado < 0:
            alerta = "stock_insuficiente"
            alertas.append(
                f"{producto.nombre}: stock insuficiente (disponible {q4(stock_actual)}, "
                f"solicitado {q4(conversion.cantidad_base)})"
            )

        total += subtotal
        costo_estimado += q2(conversion.cantidad_base * costo_base)

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
                "precio_unitario": num(q2(precio)),
                "subtotal": str(subtotal),
                "stock_actual_base": num(q4(stock_actual)),
                "stock_resultante_base": num(q4(resultado)),
                "costo_base": str(costo_base),
                "alerta": alerta,
            }
        )

    return {
        "total": num(q2(total)),
        "costo_estimado": num(q2(costo_estimado)),
        "lineas": lineas,
        "alertas": alertas,
    }


def confirmar(db: Session, payload: dict[str, Any], usuario_id: int) -> Venta:
    """Confirma la venta: cabecera, detalles, movimientos y existencias en una transacciÃ³n."""
    clave = payload.get("idempotency_key")
    if clave:
        existente = db.execute(
            select(Venta).options(selectinload(Venta.detalles)).where(
                Venta.idempotency_key == clave
            )
        ).scalar_one_or_none()
        if existente is not None:
            return existente

    almacen = _resolver_almacen(db, payload.get("almacen_id"))
    fecha = payload.get("fecha") or date.today()

    venta = Venta(
        numero="PENDIENTE",
        almacen_id=almacen.id,
        fecha=fecha,
        estado="CONFIRMADO",
        usuario_id=usuario_id,
        total=0,
        costo_total=0,
        idempotency_key=clave,
        cliente=(payload.get("cliente") or "").strip() or None,
        observaciones=payload.get("observaciones"),
    )
    db.add(venta)
    db.flush()
    venta.numero = siguiente_numero(db, "VENTA", almacen.id)

    total = Decimal("0")
    costo_total = Decimal("0")

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
        precio = (
            dec(linea["precio_unitario"])
            if linea.get("precio_unitario") is not None
            else dec(presentacion.precio_venta)
        )
        subtotal = q2(cantidad * precio)

        existencia = inventario.bloquear_existencia(db, almacen.id, producto.id)
        stock_actual = dec(existencia.cantidad_base)
        costo_base = dec(existencia.costo_promedio_base)

        if conversion.cantidad_base > stock_actual:
            raise ErrorStockInsuficiente(
                f"No hay stock suficiente de Â«{producto.nombre}Â».",
                detalle={
                    "producto_id": producto.id,
                    "producto": producto.nombre,
                    "cantidad_solicitada": num(q4(conversion.cantidad_base)),
                    "saldo_disponible": num(q4(stock_actual)),
                    "unidad_base": producto.unidad_base.nombre if producto.unidad_base else None,
                },
            )

        inventario.aplicar_salida(
            db,
            almacen_id=almacen.id,
            producto_id=producto.id,
            cantidad_base=conversion.cantidad_base,
            tipo=TipoMovimiento.VENTA,
            origen_tipo="VENTA",
            origen_id=venta.id,
            usuario_id=usuario_id,
            referencia=venta.numero,
        )

        costo_linea = q2(conversion.cantidad_base * costo_base)
        db.add(
            DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                presentacion_id=presentacion.id,
                cantidad=q4(cantidad),
                factor_snapshot=dec(presentacion.factor_base),
                cantidad_base=q4(conversion.cantidad_base),
                precio_unitario=q2(precio),
                costo_base_snapshot=costo_base,
                subtotal=subtotal,
                costo_total_linea=costo_linea,
            )
        )
        total += subtotal
        costo_total += costo_linea

    venta.total = q2(total)
    venta.costo_total = q2(costo_total)
    db.flush()
    return venta


def anular(db: Session, venta_id: int, motivo: str, usuario_id: int) -> Venta:
    """Anula una venta confirmada: conserva la original y genera contramovimientos."""
    venta = db.execute(
        select(Venta).options(selectinload(Venta.detalles)).where(Venta.id == venta_id)
    ).scalar_one_or_none()
    if venta is None:
        raise ErrorNegocio("La venta no existe.", detalle={"venta_id": venta_id})
    if venta.estado != "CONFIRMADO":
        raise ErrorNegocio(
            "La venta ya fue anulada o no estÃ¡ confirmada.",
            detalle={"estado": venta.estado.value},
        )

    for detalle in venta.detalles:
        existencia = inventario.bloquear_existencia(db, venta.almacen_id, detalle.producto_id)
        stock_actual = dec(existencia.cantidad_base)
        if stock_actual < dec(detalle.cantidad_base):
            raise ErrorStockInsuficiente(
                "No se puede anular: el stock actual es menor que el devuelto por la venta.",
                detalle={
                    "producto_id": detalle.producto_id,
                    "cantidad_a_devolver": num(q4(dec(detalle.cantidad_base))),
                    "saldo_disponible": num(q4(stock_actual)),
                },
            )
        inventario.aplicar_entrada(
            db,
            almacen_id=venta.almacen_id,
            producto_id=detalle.producto_id,
            cantidad_base=dec(detalle.cantidad_base),
            costo_unitario_base=dec(detalle.costo_base_snapshot),
            tipo=TipoMovimiento.REVERSO_VENTA,
            origen_tipo="VENTA",
            origen_id=venta.id,
            usuario_id=usuario_id,
            referencia=venta.numero,
        )

    venta.estado = "ANULADO"
    venta.anulado_por_id = usuario_id
    venta.anulado_at = datetime.now(timezone.utc)
    venta.motivo_anulacion = motivo
    db.flush()
    return venta


def venta_a_dict(venta: Venta) -> dict[str, Any]:
    detalles = []
    for d in venta.detalles:
        producto = d.producto
        presentacion = d.presentacion
        detalles.append(
            {
                "id": d.id,
                "producto_id": d.producto_id,
                "presentacion_id": d.presentacion_id,
                "cantidad": num(q4(dec(d.cantidad))),
                "factor_snapshot": num(d.factor_snapshot),
                "cantidad_base": num(q4(dec(d.cantidad_base))),
                "precio_unitario": num(q2(dec(d.precio_unitario))),
                "subtotal": num(q2(dec(d.subtotal))),
                "costo_total_linea": num(q2(dec(d.costo_total_linea))),
                "producto_codigo": producto.codigo if producto else None,
                "producto_nombre": producto.nombre if producto else None,
                "presentacion_nombre": presentacion.nombre if presentacion else None,
            }
        )
    return {
        "id": venta.id,
        "numero": venta.numero,
        "almacen_id": venta.almacen_id,
        "fecha": venta.fecha,
        "estado": venta.estado.value,
        "total": num(q2(dec(venta.total))),
        "costo_total": num(q2(dec(venta.costo_total))),
        "cliente": venta.cliente,
        "observaciones": venta.observaciones,
        "usuario": venta.usuario.nombre if venta.usuario else None,
        "created_at": venta.created_at,
        "detalles": detalles,
    }


__all__ = ["anular", "confirmar", "previsualizar", "venta_a_dict"]

