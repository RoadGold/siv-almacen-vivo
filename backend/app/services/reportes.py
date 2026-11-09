"""Reportes e indicadores (plan §5.7, Fase 9).

Todas las cifras se calculan en el servidor con agregaciones SQL y se devuelven
como cadenas decimales. El margen se etiqueta siempre como **margen bruto
estimado** (ventas menos costo de mercadería vendida), nunca como utilidad neta.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Abastecimiento,
    Categoria,
    DetalleAbastecimiento,
    DetalleVenta,
    Existencia,
    Producto,
    Proveedor,
    Venta,
)
from app.domain.unidades import dec, num, q2


def _periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hoy = date.today()
    inicio = desde or date(hoy.year, hoy.month, 1)
    fin = hasta or hoy
    return inicio, fin


def ventas_por_periodo(
    db: Session, *, desde: date | None = None, hasta: date | None = None
) -> dict[str, Any]:
    inicio, fin = _periodo(desde, hasta)
    filas = db.execute(
        select(
            func.date(Venta.fecha).label("dia"),
            func.count(func.distinct(Venta.id)).label("operaciones"),
            func.coalesce(func.sum(Venta.total), 0).label("total"),
            func.coalesce(func.sum(Venta.costo_total), 0).label("costo"),
        )
        .where(
            Venta.fecha.between(inicio, fin),
            Venta.estado == "CONFIRMADO",
        )
        .group_by(func.date(Venta.fecha))
        .order_by(func.date(Venta.fecha))
    ).all()

    detalle = []
    total = Decimal("0")
    costo = Decimal("0")
    operaciones = 0
    for dia, cantidad, suma, costo_dia in filas:
        total += dec(suma)
        costo += dec(costo_dia)
        operaciones += cantidad
        detalle.append(
            {
                "fecha": dia.isoformat(),
                "operaciones": cantidad,
                "total": num(q2(dec(suma))),
                "costo": num(q2(dec(costo_dia))),
                "margen_bruto_estimado": num(q2(dec(suma) - dec(costo_dia))),
            }
        )

    return {
        "desde": inicio.isoformat(),
        "hasta": fin.isoformat(),
        "operaciones": operaciones,
        "total": num(q2(total)),
        "costo": num(q2(costo)),
        "margen_bruto_estimado": num(q2(total - costo)),
        "por_dia": detalle,
    }


def ventas_por_producto(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = 50,
) -> list[dict[str, Any]]:
    inicio, fin = _periodo(desde, hasta)
    filas = db.execute(
        select(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            func.coalesce(func.sum(DetalleVenta.cantidad_base), 0).label("cantidad_base"),
            func.coalesce(func.sum(DetalleVenta.subtotal), 0).label("total"),
            func.coalesce(func.sum(DetalleVenta.costo_total_linea), 0).label("costo"),
        )
        .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .where(Venta.fecha.between(inicio, fin), Venta.estado == "CONFIRMADO")
        .group_by(Producto.id, Producto.codigo, Producto.nombre)
        .order_by(func.sum(DetalleVenta.subtotal).desc())
        .limit(limite)
    ).all()

    return [
        {
            "producto_id": id_,
            "codigo": codigo,
            "producto": nombre,
            "cantidad_base": num(dec(cantidad)),
            "total": num(q2(dec(total))),
            "costo": num(q2(dec(costo))),
            "margen_bruto_estimado": num(q2(dec(total) - dec(costo))),
        }
        for id_, codigo, nombre, cantidad, total, costo in filas
    ]


def ventas_por_categoria(
    db: Session, *, desde: date | None = None, hasta: date | None = None
) -> list[dict[str, Any]]:
    inicio, fin = _periodo(desde, hasta)
    filas = db.execute(
        select(
            func.coalesce(Categoria.nombre, "Sin categoría").label("categoria"),
            func.coalesce(func.sum(DetalleVenta.subtotal), 0).label("total"),
            func.coalesce(func.sum(DetalleVenta.costo_total_linea), 0).label("costo"),
            func.count(func.distinct(DetalleVenta.venta_id)).label("operaciones"),
        )
        .select_from(DetalleVenta)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .join(Producto, Producto.id == DetalleVenta.producto_id)
        .outerjoin(Categoria, Categoria.id == Producto.categoria_id)
        .where(Venta.fecha.between(inicio, fin), Venta.estado == "CONFIRMADO")
        .group_by(Categoria.nombre)
        .order_by(func.sum(DetalleVenta.subtotal).desc())
    ).all()

    return [
        {
            "categoria": categoria,
            "operaciones": operaciones,
            "total": num(q2(dec(total))),
            "costo": num(q2(dec(costo))),
            "margen_bruto_estimado": num(q2(dec(total) - dec(costo))),
        }
        for categoria, total, costo, operaciones in filas
    ]


def ventas_por_usuario(
    db: Session, *, desde: date | None = None, hasta: date | None = None
) -> list[dict[str, Any]]:
    from app.db.models import Usuario

    inicio, fin = _periodo(desde, hasta)
    filas = db.execute(
        select(
            Usuario.nombre,
            func.count(Venta.id).label("operaciones"),
            func.coalesce(func.sum(Venta.total), 0).label("total"),
        )
        .join(Venta, Venta.usuario_id == Usuario.id)
        .where(Venta.fecha.between(inicio, fin), Venta.estado == "CONFIRMADO")
        .group_by(Usuario.nombre)
        .order_by(func.sum(Venta.total).desc())
    ).all()

    return [
        {
            "usuario": nombre,
            "operaciones": operaciones,
            "total": num(q2(dec(total))),
        }
        for nombre, operaciones, total in filas
    ]


def abastecimientos_por_proveedor(
    db: Session, *, desde: date | None = None, hasta: date | None = None
) -> list[dict[str, Any]]:
    inicio, fin = _periodo(desde, hasta)
    filas = db.execute(
        select(
            Proveedor.id,
            Proveedor.razon_social,
            func.count(Abastecimiento.id).label("operaciones"),
            func.coalesce(func.sum(Abastecimiento.total), 0).label("total"),
            func.max(Abastecimiento.fecha).label("ultimo_ingreso"),
        )
        .join(Abastecimiento, Abastecimiento.proveedor_id == Proveedor.id)
        .where(Abastecimiento.fecha.between(inicio, fin))
        .group_by(Proveedor.id, Proveedor.razon_social)
        .order_by(func.sum(Abastecimiento.total).desc())
    ).all()

    return [
        {
            "proveedor_id": id_,
            "proveedor": razon_social,
            "operaciones": operaciones,
            "total": num(q2(dec(total))),
            "ultimo_ingreso": ultimo.isoformat() if ultimo else None,
        }
        for id_, razon_social, operaciones, total, ultimo in filas
    ]


def historico_de_costos(
    db: Session, *, producto_id: int | None = None, proveedor_id: int | None = None
) -> list[dict[str, Any]]:
    consulta = (
        select(
            Producto.codigo,
            Producto.nombre,
            Proveedor.razon_social,
            DetalleAbastecimiento.cantidad,
            DetalleAbastecimiento.costo_unitario,
            DetalleAbastecimiento.factor_snapshot,
            Abastecimiento.fecha,
            Abastecimiento.documento,
        )
        .join(DetalleAbastecimiento, DetalleAbastecimiento.producto_id == Producto.id)
        .join(Abastecimiento, Abastecimiento.id == DetalleAbastecimiento.abastecimiento_id)
        .join(Proveedor, Proveedor.id == Abastecimiento.proveedor_id)
        .where(Abastecimiento.estado == "CONFIRMADO")
    )
    if producto_id is not None:
        consulta = consulta.where(DetalleAbastecimiento.producto_id == producto_id)
    if proveedor_id is not None:
        consulta = consulta.where(Abastecimiento.proveedor_id == proveedor_id)

    filas = db.execute(
        consulta.order_by(
            Abastecimiento.fecha.desc(), DetalleAbastecimiento.id.desc()
        ).limit(500)
    ).all()

    return [
        {
            "codigo": codigo,
            "producto": nombre,
            "proveedor": proveedor,
            "cantidad": num(dec(cantidad)),
            "costo_unitario": num(q2(dec(costo_unitario))),
            "factor": num(dec(factor)),
            "fecha": fecha.isoformat(),
            "documento": documento,
        }
        for codigo, nombre, proveedor, cantidad, costo_unitario, factor, fecha, documento in filas
    ]


def inventario_valorizado(
    db: Session, *, almacen_id: int | None = None
) -> list[dict[str, Any]]:
    filtros = [Existencia.cantidad_base != 0]
    if almacen_id is not None:
        filtros.append(Existencia.almacen_id == almacen_id)

    filas = db.execute(
        select(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            Existencia.cantidad_base,
            Existencia.costo_promedio_base,
        )
        .join(Producto, Producto.id == Existencia.producto_id)
        .where(*filtros)
    ).all()

    resultado = []
    for id_, codigo, nombre, cantidad, costo in filas:
        valor = dec(cantidad) * dec(costo)
        resultado.append(
            {
                "producto_id": id_,
                "codigo": codigo,
                "producto": nombre,
                "cantidad_base": num(dec(cantidad)),
                "costo_promedio_base": num(dec(costo)),
                "valor_costo": num(q2(valor)),
            }
        )
    resultado.sort(key=lambda item: Decimal(item["valor_costo"]), reverse=True)
    return resultado


def margen_bruto(
    db: Session, *, desde: date | None = None, hasta: date | None = None
) -> dict[str, Any]:
    """Margen bruto estimado = ventas − costo de mercadería vendida."""
    inicio, fin = _periodo(desde, hasta)
    fila = db.execute(
        select(
            func.coalesce(func.sum(Venta.total), 0),
            func.coalesce(func.sum(Venta.costo_total), 0),
            func.count(Venta.id),
        ).where(
            Venta.fecha.between(inicio, fin),
            Venta.estado == "CONFIRMADO",
        )
    ).one()
    total = dec(fila[0])
    costo = dec(fila[1])
    margen = total - costo
    porcentaje = (margen / total * Decimal("100")) if total else Decimal("0")
    return {
        "desde": inicio.isoformat(),
        "hasta": fin.isoformat(),
        "operaciones": fila[2],
        "ventas": num(q2(total)),
        "costo_mercaderia_vendida": num(q2(costo)),
        "margen_bruto_estimado": num(q2(margen)),
        "margen_bruto_porcentaje": num(porcentaje.quantize(Decimal("0.01"))),
        "nota": "Margen bruto estimado: ventas menos costo de mercadería vendida. No es utilidad neta.",
    }


def exportar_ventas_csv(
    db: Session, *, desde: date | None = None, hasta: date | None = None
) -> bytes:
    """Exporta el detalle de ventas del periodo en CSV compatible con Excel."""
    inicio, fin = _periodo(desde, hasta)
    filas = db.execute(
        select(
            Venta.numero,
            Venta.fecha,
            Venta.estado,
            Producto.codigo,
            Producto.nombre,
            DetalleVenta.cantidad,
            DetalleVenta.precio_unitario,
            DetalleVenta.subtotal,
            DetalleVenta.costo_total_linea,
        )
        .select_from(DetalleVenta)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .join(Producto, Producto.id == DetalleVenta.producto_id)
        .where(Venta.fecha.between(inicio, fin))
        .order_by(Venta.fecha, Venta.id, DetalleVenta.id)
    ).all()

    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(
        [
            "Numero",
            "Fecha",
            "Estado",
            "Codigo",
            "Producto",
            "Cantidad",
            "Precio unitario",
            "Subtotal",
            "Costo de la linea",
        ]
    )
    for numero, fecha, estado, codigo, nombre, cantidad, precio, subtotal, costo in filas:
        escritor.writerow(
            [
                numero,
                fecha.isoformat(),
                estado.value if hasattr(estado, "value") else estado,
                codigo,
                nombre,
                num(dec(cantidad)),
                num(q2(dec(precio))),
                num(q2(dec(subtotal))),
                num(q2(dec(costo))),
            ]
        )
    # BOM para que Excel reconozca UTF-8.
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


__all__ = [
    "abastecimientos_por_proveedor",
    "exportar_ventas_csv",
    "historico_de_costos",
    "inventario_valorizado",
    "margen_bruto",
    "ventas_por_categoria",
    "ventas_por_periodo",
    "ventas_por_producto",
    "ventas_por_usuario",
]
