"""Servicio de lotes de inventario.

Un lote es una porción de existencias con su propio costo y sus propios precios
de venta. Nace de un ingreso de mercadería (o de una carga inicial) y se
conserva aunque se agote, para no perder la trazabilidad.

El precio de venta de un lote se define **por presentación**: un mismo lote
puede venderse como saco, por kilo o por medio saco, cada uno con su precio.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    LoteInventario,
    LotePrecio,
    PresentacionProducto,
    Producto,
)
from app.domain.unidades import ErrorNegocio, dec, num, q2, q4

ESTADO_ACTIVO = "ACTIVO"
ESTADO_INHABILITADO = "INHABILITADO"


def _presentacion_del_lote(
    lote: LoteInventario, producto: Producto | None
) -> PresentacionProducto | None:
    if getattr(lote, "presentacion_principal", None) is not None:
        return lote.presentacion_principal
    for item in lote.precios:
        if item.presentacion is not None and item.presentacion_id == lote.presentacion_principal_id:
            return item.presentacion
    for item in lote.precios:
        if item.presentacion is not None:
            return item.presentacion
    if producto is not None:
        activas = [p for p in producto.presentaciones if p.activo]
        if activas:
            return max(activas, key=lambda p: dec(p.factor_base))
    return None


def _lote_a_dict(lote: LoteInventario, producto: Producto | None = None) -> dict[str, Any]:
    precios = [
        {
            "presentacion_id": precio.presentacion_id,
            "presentacion_nombre": precio.presentacion.nombre if precio.presentacion else "",
            "factor_base": (
                num(dec(precio.presentacion.factor_base)) if precio.presentacion else "1"
            ),
            "precio": num(dec(precio.precio)),
        }
        for precio in sorted(lote.precios, key=lambda item: item.presentacion_id)
    ]
    cantidad = dec(lote.cantidad_disponible)
    cantidad_ini = dec(lote.cantidad_inicial)
    valores = [dec(p["precio"]) for p in precios]
    presentacion = _presentacion_del_lote(lote, producto)
    factor = dec(presentacion.factor_base) if presentacion and dec(presentacion.factor_base) > 0 else Decimal("1")
    transporte = dec(getattr(lote, "costo_transporte", 0) or 0)
    unidad_base = (
        producto.unidad_base.nombre
        if producto is not None and getattr(producto, "unidad_base", None) is not None
        else None
    )
    unidades_del_lote = (cantidad_ini / factor) if factor > 0 else Decimal("0")
    transporte_unitario = (
        q2(transporte / unidades_del_lote) if unidades_del_lote > 0 else Decimal("0")
    )
    return {
        "id": lote.id,
        "producto_id": lote.producto_id,
        "producto_codigo": producto.codigo if producto else None,
        "producto_nombre": producto.nombre if producto else None,
        "unidad_base": unidad_base,
        "presentacion_id": lote.presentacion_principal_id or (presentacion.id if presentacion else None),
        "presentacion_nombre": presentacion.nombre if presentacion else None,
        "factor_base": num(factor),
        "codigo_lote": lote.codigo_lote,
        "fecha_ingreso": lote.fecha_ingreso.isoformat() if lote.fecha_ingreso else None,
        "cantidad_inicial": num(q4(cantidad_ini)),
        "cantidad_disponible": num(q4(cantidad)),
        "cantidad_inicial_presentacion": num(q4(unidades_del_lote)),
        "cantidad_disponible_presentacion": num(q4(cantidad / factor)),
        "costo_base": num(dec(lote.costo_base)),
        "costo_unitario": num(q2(dec(lote.costo_unitario))),
        "costo_transporte": num(q2(transporte)),
        "costo_transporte_unitario": num(transporte_unitario),
        "precio_venta": num(q2(dec(lote.precio_venta))),
        "almacen_id": lote.almacen_id,
        "abastecimiento_id": lote.abastecimiento_id,
        "proveedor_id": getattr(lote, "proveedor_id", None),
        "proveedor_nombre": (
            getattr(lote.proveedor, "razon_social", None)
            if getattr(lote, "proveedor", None) is not None
            else None
        ),
        "estado": "AGOTADO" if cantidad <= 0 else lote.estado,
        "origen": lote.origen,
        "precios": precios,
        "precio_minimo": num(min(valores)) if valores else None,
        "precio_maximo": num(max(valores)) if valores else None,
        "tiene_precios_distintos": bool(valores) and (min(valores) != max(valores)),
    }


def listar_lotes(
    db: Session,
    producto_id: int,
    *,
    almacen_id: int | None = None,
    solo_con_stock: bool = False,
    incluir_agotados: bool = True,
) -> list[dict[str, Any]]:
    """Lotes de un producto, del más antiguo al más reciente (PEPS)."""
    consulta = (
        select(LoteInventario)
        .options(
            selectinload(LoteInventario.presentacion_principal),
            selectinload(LoteInventario.precios).selectinload(LotePrecio.presentacion),
        )
        .where(LoteInventario.producto_id == producto_id)
    )
    if almacen_id is not None:
        consulta = consulta.where(LoteInventario.almacen_id == almacen_id)
    if solo_con_stock:
        consulta = consulta.where(LoteInventario.cantidad_disponible > 0)
    if not incluir_agotados:
        consulta = consulta.where(LoteInventario.cantidad_disponible > 0)

    lotes = db.execute(
        consulta.order_by(
            LoteInventario.fecha_ingreso.asc().nulls_last(),
            LoteInventario.id.asc(),
        )
    ).scalars().all()
    producto = db.execute(
        select(Producto)
        .options(selectinload(Producto.unidad_base), selectinload(Producto.presentaciones))
        .where(Producto.id == producto_id)
    ).scalar_one_or_none()
    return [_lote_a_dict(lote, producto) for lote in lotes]


def lotes_disponibles(
    db: Session, producto_id: int, almacen_id: int | None = None
) -> list[dict[str, Any]]:
    """Lotes con existencias disponibles (para la selección en la caja)."""
    return listar_lotes(db, producto_id, almacen_id=almacen_id, solo_con_stock=True)


def obtener_lote(db: Session, lote_id: int) -> LoteInventario:
    lote = db.execute(
        select(LoteInventario)
        .options(
            selectinload(LoteInventario.presentacion_principal),
            selectinload(LoteInventario.precios).selectinload(LotePrecio.presentacion),
        )
        .where(LoteInventario.id == lote_id)
    ).scalar_one_or_none()
    if lote is None:
        raise ErrorNegocio("El lote no existe.", detalle={"lote_id": lote_id})
    return lote


def generar_codigo_lote(db: Session, producto: Producto) -> str:
    """Código único: CODIGO_PRODUCTO-L001, L002…"""
    total = db.execute(
        select(func.count())
        .select_from(LoteInventario)
        .where(LoteInventario.producto_id == producto.id)
    ).scalar_one()
    return f"{producto.codigo}-L{total + 1:03d}"


def _precios_del_lote(
    db: Session,
    lote: LoteInventario,
    presentacion_principal: PresentacionProducto,
    precio_presentacion: Decimal,
    precio_venta: Decimal | None = None,
) -> None:
    """Registra el precio del lote en todas las presentaciones de venta del producto.

    La presentación con la que ingresó el lote usa el precio indicado; las demás
    heredan el precio vigente del catálogo (para poder vender el mismo lote por
    kilo o por medio saco).
    """
    producto = db.get(Producto, lote.producto_id)
    if producto is None:
        return
    presentaciones = [
        presentacion
        for presentacion in producto.presentaciones
        if presentacion.activo and presentacion.es_venta
    ]
    for presentacion in presentaciones:
        if presentacion.id == presentacion_principal.id:
            precio = precio_presentacion
        elif precio_venta is not None and presentacion.id == presentacion_principal.id:
            precio = precio_venta
        else:
            precio = dec(presentacion.precio_venta)
        db.add(
            LotePrecio(
                lote_id=lote.id,
                presentacion_id=presentacion.id,
                precio=q2(precio),
            )
        )
    db.flush()


def crear_lote(
    db: Session,
    *,
    producto_id: int,
    almacen_id: int,
    cantidad_base: Decimal,
    cantidad_inicial: Decimal | None = None,
    costo_base: Decimal = Decimal("0"),
    costo_unitario: Decimal = Decimal("0"),
    costo_transporte: Decimal = Decimal("0"),
    precio_venta: Decimal = Decimal("0"),
    presentacion_id: int | None = None,
    fecha_ingreso: date | None = None,
    abastecimiento_id: int | None = None,
    detalle_abastecimiento_id: int | None = None,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    origen: str = "RECEPCION",
    codigo: str | None = None,
) -> LoteInventario:
    """Crea un lote con su stock, su costo y sus precios de venta.

    `proveedor_id` es el proveedor que suministró la mercadería: es lo que
    permite atribuir después la venta de este lote a su proveedor.
    """
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise ErrorNegocio("El producto del lote no existe.", detalle={"producto_id": producto_id})

    lote = LoteInventario(
        producto_id=producto_id,
        codigo_lote=codigo or generar_codigo_lote(db, producto),
        fecha_ingreso=fecha_ingreso,
        cantidad_inicial=q4(cantidad_inicial if cantidad_inicial is not None else cantidad_base),
        # El disponible lo suma el movimiento de inventario (una sola via de entrada).
        cantidad_disponible=q4(Decimal("0")),
        costo_base=dec(costo_base),
        costo_unitario=q2(costo_unitario),
        costo_transporte=q2(costo_transporte),
        precio_venta=q2(precio_venta),
        presentacion_principal_id=presentacion_id,
        almacen_id=almacen_id,
        abastecimiento_id=abastecimiento_id,
        detalle_abastecimiento_id=detalle_abastecimiento_id,
        proveedor_id=proveedor_id,
        estado=ESTADO_ACTIVO,
        origen=origen,
        usuario_id=usuario_id,
    )
    db.add(lote)
    db.flush()

    if presentacion_id is not None:
        presentacion = db.get(PresentacionProducto, presentacion_id)
        if presentacion is not None:
            _precios_del_lote(db, lote, presentacion, q2(precio_venta))
    db.flush()
    return lote


def precio_del_lote(db: Session, lote_id: int, presentacion_id: int) -> Decimal | None:
    """Precio de una presentación dentro de un lote (None si no lo tiene)."""
    fila = db.execute(
        select(LotePrecio).where(
            LotePrecio.lote_id == lote_id,
            LotePrecio.presentacion_id == presentacion_id,
        )
    ).scalar_one_or_none()
    return dec(fila.precio) if fila is not None else None


def actualizar_precio_lote(
    db: Session,
    lote_id: int,
    presentacion_id: int,
    precio: Decimal,
    usuario_id: int | None = None,
    motivo: str | None = None,
) -> dict[str, Any]:
    """Cambia el precio de una presentación de un lote y deja auditoría."""
    from app.services import auditoria

    lote = obtener_lote(db, lote_id)
    fila = db.execute(
        select(LotePrecio).where(
            LotePrecio.lote_id == lote_id,
            LotePrecio.presentacion_id == presentacion_id,
        )
    ).scalar_one_or_none()
    anterior = dec(fila.precio) if fila is not None else Decimal("0")
    if fila is None:
        fila = LotePrecio(
            lote_id=lote_id,
            presentacion_id=presentacion_id,
            precio=q2(precio),
        )
        db.add(fila)
    else:
        fila.precio = q2(precio)
    if lote.presentacion_principal_id == presentacion_id:
        lote.precio_venta = q2(precio)
    db.flush()

    auditoria.registrar(
        db,
        accion="lote.precio.actualizar",
        entidad="lote",
        entidad_id=lote_id,
        actor_id=usuario_id,
        detalle={
            "codigo_lote": lote.codigo_lote,
            "presentacion_id": presentacion_id,
            "precio_anterior": num(q2(anterior)),
            "precio_nuevo": num(q2(precio)),
            "motivo": motivo,
        },
    )
    return {
        "lote_id": lote_id,
        "presentacion_id": presentacion_id,
        "precio_anterior": num(q2(anterior)),
        "precio_nuevo": num(q2(precio)),
    }


def costo_promedio_de_lotes(db: Session, producto_id: int, almacen_id: int) -> Decimal:
    """Costo promedio de los lotes con existencias (para la existencia consolidada)."""
    total_cantidad = Decimal("0")
    total_valor = Decimal("0")
    for lote in db.execute(
        select(LoteInventario).where(
            LoteInventario.producto_id == producto_id,
            LoteInventario.almacen_id == almacen_id,
            LoteInventario.cantidad_disponible > 0,
        )
    ).scalars().all():
        cantidad = dec(lote.cantidad_disponible)
        total_cantidad += cantidad
        total_valor += cantidad * dec(lote.costo_base)
    if total_cantidad <= 0:
        return Decimal("0")
    return total_valor / total_cantidad


__all__ = [
    "ESTADO_ACTIVO",
    "ESTADO_INHABILITADO",
    "actualizar_precio_lote",
    "costo_promedio_de_lotes",
    "crear_lote",
    "generar_codigo_lote",
    "listar_lotes",
    "lotes_disponibles",
    "obtener_lote",
    "precio_del_lote",
]
