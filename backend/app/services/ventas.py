"""Servicio de ventas (Fase 7 · punto de venta).

Reglas clave:
- El servidor recalcula precios, conversiones y disponibilidad: nunca confía en el total del navegador.
- La confirmación es idempotente: la misma `idempotency_key` devuelve la misma venta.
- Venta + detalles + movimientos + existencias ocurren en una única transacción.
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
    LoteInventario,
    PresentacionProducto,
    Producto,
    TipoMovimiento,
    Venta,
)
from app.domain.precios import ResultadoPrecioLinea, evaluar_precio_linea
from app.domain.unidades import ErrorNegocio, ErrorStockInsuficiente, convertir_a_base, dec, num, q2, q4
from app.services import configuracion, inventario
from app.services.secuencias import siguiente_numero


class ErrorPrecioNoPermitido(ErrorNegocio):
    """El precio solicitado supera el límite de descuento de la caja."""

    codigo = "precio_fuera_de_limite"
    http_status = 409


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
            f"El producto «{producto.nombre}» está desactivado y no puede venderse.",
            detalle={"producto_id": producto.id},
        )
    if not presentacion.activo or not presentacion.es_venta:
        raise ErrorNegocio(
            f"La presentación «{presentacion.nombre}» no está disponible para venta.",
            detalle={"presentacion_id": presentacion.id},
        )
    return producto, presentacion


def _precio_de_lista(
    db: Session, linea: dict[str, Any], presentacion: PresentacionProducto
) -> tuple[Decimal, dict[str, Any] | None]:
    """Precio de lista y lote de la línea.

    Si la línea indica un lote, el precio de lista es **el del lote** (cada
    temporada tiene su precio). Si no, es el de la presentación (comportamiento
    histórico).
    """
    lote_id = linea.get("lote_id")
    if lote_id:
        from app.services import lotes as servicio_lotes

        lote = db.get(LoteInventario, lote_id)
        if lote is None:
            raise ErrorNegocio(
                "El lote indicado en la línea no existe.",
                detalle={"lote_id": lote_id},
            )
        precio = servicio_lotes.precio_del_lote(db, lote.id, presentacion.id)
        if precio is None:
            precio = dec(presentacion.precio_venta)
        return precio, {
            "id": lote.id,
            "codigo_lote": lote.codigo_lote,
            "fecha_ingreso": lote.fecha_ingreso.isoformat() if lote.fecha_ingreso else None,
            "cantidad_disponible": num(q4(dec(lote.cantidad_disponible))),
            "costo_base": num(dec(lote.costo_base)),
        }
    return dec(presentacion.precio_venta), None


def _evaluar_linea(
    db: Session,
    linea: dict[str, Any],
    presentacion: PresentacionProducto,
    *,
    puede_editar_precio: bool,
    puede_administrar_precios: bool,
) -> ResultadoPrecioLinea:
    """Aplica la regla de precio a una línea de la venta.

    Lo que el vendedor ajusta es el **total de la línea**; el precio unitario
    se deriva de él.
    """
    precio_lista, _ = _precio_de_lista(db, linea, presentacion)
    return evaluar_precio_linea(
        precio_lista,
        linea.get("cantidad") or 1,
        precio_unitario_solicitado=linea.get("precio_unitario"),
        precio_total_solicitado=linea.get("precio_total"),
        puede_editar_precio=puede_editar_precio,
        puede_administrar_precios=puede_administrar_precios,
        limite_porcentaje=configuracion.decimal(
            db, "venta_descuento_maximo_porcentaje", "20"
        ),
        limite_monto=configuracion.decimal(db, "venta_descuento_maximo_monto", "0"),
    )


def previsualizar(
    db: Session,
    payload: dict[str, Any],
    *,
    puede_editar_precio: bool = False,
    puede_administrar_precios: bool = False,
) -> dict[str, Any]:
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
        precio = _evaluar_linea(
            db,
            linea,
            presentacion,
            puede_editar_precio=puede_editar_precio,
            puede_administrar_precios=puede_administrar_precios,
        )
        _, info_lote = _precio_de_lista(db, linea, presentacion)
        subtotal = q2(precio.precio_total)

        existencia = inventario.existencia_actual(db, almacen.id, producto.id)
        stock_actual = dec(existencia.cantidad_base) if existencia else Decimal("0")
        costo_base = dec(existencia.costo_promedio_base) if existencia else Decimal("0")
        if info_lote:
            costo_base = dec(info_lote["costo_base"])
        resultado = stock_actual - conversion.cantidad_base

        alerta = None
        if resultado < 0:
            alerta = "stock_insuficiente"
            alertas.append(
                f"{producto.nombre}: stock insuficiente (disponible {q4(stock_actual)}, "
                f"solicitado {q4(conversion.cantidad_base)})"
            )
        if info_lote and dec(info_lote["cantidad_disponible"]) < conversion.cantidad_base:
            alerta = "stock_insuficiente"
            alertas.append(
                f"{producto.nombre} (lote {info_lote['codigo_lote']}): el lote no tiene "
                f"{q4(conversion.cantidad_base)} (disponible {info_lote['cantidad_disponible']})"
            )
        if not precio.permitido:
            alerta = "precio_fuera_de_limite"
            alertas.append(
                f"{producto.nombre} ({presentacion.nombre}): {precio.motivo or 'precio no permitido'}"
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
                "precio_unitario": num(q2(precio.precio_unitario)),
                "precio_original": num(q2(precio.precio_original_unitario)),
                "precio_total": num(q2(precio.precio_total)),
                "precio_total_original": num(q2(precio.total_original)),
                "descuento_porcentaje": num(q4(precio.descuento_porcentaje)),
                "descuento_monto": num(q2(precio.descuento_monto)),
                "precio_permitido": precio.permitido,
                "motivo_precio": linea.get("motivo_precio"),
                "lote_id": info_lote["id"] if info_lote else None,
                "lote_codigo": info_lote["codigo_lote"] if info_lote else None,
                "lote_fecha_ingreso": info_lote["fecha_ingreso"] if info_lote else None,
                "lote_stock_disponible": (
                    info_lote["cantidad_disponible"] if info_lote else None
                ),
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


def _monto_recibido(db: Session, payload: dict[str, Any], total: Decimal) -> Decimal | None:
    """Efectivo recibido por el cliente (opcional)."""
    from app.domain.unidades import dec as _dec

    valor = payload.get("monto_recibido")
    if valor is None or str(valor).strip() == "":
        return None
    try:
        monto = _dec(valor)
    except Exception:
        return None
    return q2(monto)


def _vuelto(monto_recibido: Decimal | None, total: Decimal) -> Decimal | None:
    if monto_recibido is None:
        return None
    return q2(monto_recibido - total) if monto_recibido >= total else q2(Decimal("0"))


def _auditar_precio(
    db: Session,
    venta: Venta,
    producto: Producto,
    presentacion: PresentacionProducto,
    precio: ResultadoPrecio,
    linea: dict[str, Any],
    usuario_id: int,
) -> None:
    """Deja constancia de cada cambio de precio aplicado en la caja."""
    from app.services import auditoria

    auditoria.registrar(
        db,
        accion="venta.precio_modificado",
        entidad="detalle_venta",
        entidad_id=venta.id,
        actor_id=usuario_id,
        detalle={
            "venta": venta.numero,
            "producto": producto.nombre,
            "presentacion": presentacion.nombre,
            "cantidad": str(q4(precio.cantidad)),
            "precio_original": str(q2(precio.precio_original_unitario)),
            "precio_aplicado": str(q2(precio.precio_unitario)),
            "total_original": str(q2(precio.total_original)),
            "total_aplicado": str(q2(precio.precio_total)),
            "descuento_porcentaje": str(q4(precio.descuento_porcentaje)),
            "motivo": (linea.get("motivo_precio") or "").strip() or None,
        },
    )


def confirmar(
    db: Session,
    payload: dict[str, Any],
    usuario_id: int,
    *,
    puede_editar_precio: bool = False,
    puede_administrar_precios: bool = False,
) -> Venta:
    """Confirma la venta: cabecera, detalles, movimientos y existencias en una transacción."""
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
        forma_pago=(payload.get("forma_pago") or "").strip() or None,
        observaciones=payload.get("observaciones"),
    )
    db.add(venta)
    db.flush()
    venta.numero = siguiente_numero(db, "VENTA", almacen.id)

    total = Decimal("0")
    costo_total = Decimal("0")
    bloqueos: list[str] = []

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
        precio = _evaluar_linea(
            db,
            linea,
            presentacion,
            puede_editar_precio=puede_editar_precio,
            puede_administrar_precios=puede_administrar_precios,
        )
        if not precio.permitido:
            bloqueos.append(
                f"{producto.nombre} ({presentacion.nombre}): {precio.motivo or 'precio no permitido'}"
            )
        subtotal = q2(precio.precio_total)

        existencia = inventario.bloquear_existencia(db, almacen.id, producto.id)
        stock_actual = dec(existencia.cantidad_base)
        costo_base = dec(existencia.costo_promedio_base)
        lote_id = linea.get("lote_id")
        lote = None
        if lote_id:
            lote = inventario.bloquear_lote(db, lote_id)
            if lote.producto_id != producto.id:
                raise ErrorNegocio(
                    "El lote indicado no corresponde al producto de la línea.",
                    detalle={"lote_id": lote_id},
                )
            disponible_lote = dec(lote.cantidad_disponible)
            if conversion.cantidad_base > disponible_lote:
                raise ErrorStockInsuficiente(
                    f"El lote {lote.codigo_lote} no tiene existencias suficientes.",
                    detalle={
                        "producto_id": producto.id,
                        "lote_id": lote.id,
                        "codigo_lote": lote.codigo_lote,
                        "cantidad_solicitada": num(q4(conversion.cantidad_base)),
                        "saldo_disponible": num(q4(disponible_lote)),
                    },
                )
            # El costo de la venta es el del lote (exacto, no un promedio).
            costo_base = dec(lote.costo_base)

        if conversion.cantidad_base > stock_actual:
            raise ErrorStockInsuficiente(
                f"No hay stock suficiente de «{producto.nombre}».",
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
            lote_id=lote.id if lote is not None else None,
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
                precio_unitario=q2(precio.precio_unitario),
                precio_original=q2(precio.precio_original_unitario),
                motivo_precio=(linea.get("motivo_precio") or "").strip() or None,
                lote_id=lote.id if lote is not None else None,
                costo_base_snapshot=costo_base,
                subtotal=subtotal,
                costo_total_linea=costo_linea,
            )
        )
        total += subtotal
        costo_total += costo_linea

        if precio.hay_cambio:
            _auditar_precio(db, venta, producto, presentacion, precio, linea, usuario_id)

    if bloqueos:
        raise ErrorPrecioNoPermitido(
            "No se puede confirmar la venta: hay precios fuera del límite permitido.",
            detalle={"lineas": bloqueos},
        )

    venta.total = q2(total)
    venta.costo_total = q2(costo_total)
    venta.monto_recibido = _monto_recibido(db, payload, total)
    venta.vuelto = _vuelto(venta.monto_recibido, total)
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
            "La venta ya fue anulada o no está confirmada.",
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
            lote_id=detalle.lote_id,
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
                "precio_original": num(q2(dec(d.precio_original or d.precio_unitario))),
                "motivo_precio": d.motivo_precio,
                "lote_id": d.lote_id,
                "descuento_porcentaje": num(
                    q4(
                        (
                            (dec(d.precio_original or d.precio_unitario) - dec(d.precio_unitario))
                            / dec(d.precio_original or d.precio_unitario)
                            * Decimal("100")
                        )
                        if dec(d.precio_original or d.precio_unitario) > 0
                        else Decimal("0")
                    )
                ),
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
        "forma_pago": venta.forma_pago,
        "monto_recibido": num(q2(dec(venta.monto_recibido))) if venta.monto_recibido is not None else None,
        "vuelto": num(q2(dec(venta.vuelto))) if venta.vuelto is not None else None,
        "observaciones": venta.observaciones,
        "usuario": venta.usuario.nombre if venta.usuario else None,
        "ticket_impreso": bool(venta.ticket_impreso),
        "impreso_at": venta.impreso_at.isoformat() if venta.impreso_at else None,
        "impresion_error": venta.impresion_error,
        "created_at": venta.created_at,
        "detalles": detalles,
    }


__all__ = ["anular", "confirmar", "previsualizar", "venta_a_dict"]

