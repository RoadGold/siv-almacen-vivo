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

from sqlalchemy import String, func, literal, select
from sqlalchemy.orm import Session

from app.db.models import (
    Abastecimiento,
    Categoria,
    DetalleAbastecimiento,
    DetalleVenta,
    Existencia,
    PresentacionProducto,
    Producto,
    Proveedor,
    UnidadMedida,
    Venta,
)
from app.domain.unidades import dec, num, q2, q4


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


def _mapa_presentacion_principal(
    db: Session, producto_ids: list[int]
) -> dict[int, tuple[str, Decimal]]:
    """Elige la presentación principal (mayor factor de conversión) de cada producto."""
    if not producto_ids:
        return {}
    filas = db.execute(
        select(
            PresentacionProducto.producto_id,
            PresentacionProducto.nombre,
            PresentacionProducto.factor_base,
        ).where(
            PresentacionProducto.producto_id.in_(producto_ids),
            PresentacionProducto.activo.is_(True),
        )
    ).all()
    mapa: dict[int, tuple[str, Decimal]] = {}
    for prod_id, nombre, factor in filas:
        factor_dec = dec(factor)
        if factor_dec <= 0:
            continue
        actual = mapa.get(prod_id)
        if actual is None or factor_dec > actual[1]:
            mapa[prod_id] = (nombre, factor_dec)
    return mapa


def ventas_por_producto(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = 100,
) -> list[dict[str, Any]]:
    inicio, fin = _periodo(desde, hasta)
    filas = db.execute(
        select(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            UnidadMedida.nombre,
            func.coalesce(func.sum(DetalleVenta.cantidad_base), 0).label("cantidad_base"),
            func.coalesce(func.sum(DetalleVenta.subtotal), 0).label("total"),
            func.coalesce(func.sum(DetalleVenta.costo_total_linea), 0).label("costo"),
        )
        .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .outerjoin(UnidadMedida, UnidadMedida.id == Producto.unidad_base_id)
        .where(Venta.fecha.between(inicio, fin), Venta.estado == "CONFIRMADO")
        .group_by(Producto.id, Producto.codigo, Producto.nombre, UnidadMedida.nombre)
        .order_by(func.sum(DetalleVenta.subtotal).desc())
        .limit(limite)
    ).all()

    mapa_pres = _mapa_presentacion_principal(db, [f[0] for f in filas])
    resultado = []
    for id_, codigo, nombre, unidad_base, cantidad, total, costo in filas:
        cant_dec = dec(cantidad)
        pres = mapa_pres.get(id_)
        factor = pres[1] if pres else Decimal("1")
        resultado.append(
            {
                "producto_id": id_,
                "codigo": codigo,
                "producto": nombre,
                "unidad_base": unidad_base,
                "presentacion_nombre": pres[0] if pres else None,
                "factor_base": num(factor),
                "cantidad_base": num(cant_dec),
                "cantidad_presentacion": num(q4(cant_dec / factor)),
                "total": num(q2(dec(total))),
                "costo": num(q2(dec(costo))),
                "margen_bruto_estimado": num(q2(dec(total) - dec(costo))),
            }
        )
    return resultado


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
    transporte_sub = (
        select(
            Abastecimiento.proveedor_id.label("prv_id"),
            func.coalesce(func.sum(DetalleAbastecimiento.costo_transporte), 0).label("transporte"),
        )
        .join(DetalleAbastecimiento, DetalleAbastecimiento.abastecimiento_id == Abastecimiento.id)
        .where(
            Abastecimiento.fecha.between(inicio, fin),
            Abastecimiento.estado == "CONFIRMADO",
        )
        .group_by(Abastecimiento.proveedor_id)
        .subquery()
    )
    filas = db.execute(
        select(
            Proveedor.id,
            Proveedor.razon_social,
            func.count(Abastecimiento.id).label("operaciones"),
            func.coalesce(func.sum(Abastecimiento.total), 0).label("total"),
            func.coalesce(func.max(transporte_sub.c.transporte), 0).label("transporte"),
            func.max(Abastecimiento.fecha).label("ultimo_ingreso"),
        )
        .join(Abastecimiento, Abastecimiento.proveedor_id == Proveedor.id)
        .outerjoin(transporte_sub, transporte_sub.c.prv_id == Proveedor.id)
        .where(
            Abastecimiento.fecha.between(inicio, fin),
            Abastecimiento.estado == "CONFIRMADO",
        )
        .group_by(Proveedor.id, Proveedor.razon_social)
        .order_by(func.sum(Abastecimiento.total).desc())
    ).all()

    return [
        {
            "proveedor_id": id_,
            "proveedor": razon_social,
            "operaciones": operaciones,
            "total": num(q2(dec(total))),
            "costo_transporte": num(q2(dec(transporte))),
            "ultimo_ingreso": ultimo.isoformat() if ultimo else None,
        }
        for id_, razon_social, operaciones, total, transporte, ultimo in filas
    ]


def historico_de_costos(
    db: Session,
    *,
    producto_id: int | None = None,
    proveedor_id: int | None = None,
    limite: int = 500,
) -> list[dict[str, Any]]:
    consulta = (
        select(
            Producto.codigo,
            Producto.nombre,
            Proveedor.razon_social,
            PresentacionProducto.nombre,
            DetalleAbastecimiento.cantidad,
            DetalleAbastecimiento.costo_unitario,
            DetalleAbastecimiento.costo_transporte,
            DetalleAbastecimiento.subtotal,
            DetalleAbastecimiento.factor_snapshot,
            Abastecimiento.fecha,
            Abastecimiento.documento,
        )
        .join(DetalleAbastecimiento, DetalleAbastecimiento.producto_id == Producto.id)
        .join(Abastecimiento, Abastecimiento.id == DetalleAbastecimiento.abastecimiento_id)
        .join(Proveedor, Proveedor.id == Abastecimiento.proveedor_id)
        .outerjoin(
            PresentacionProducto,
            PresentacionProducto.id == DetalleAbastecimiento.presentacion_id,
        )
        .where(Abastecimiento.estado == "CONFIRMADO")
    )
    if producto_id is not None:
        consulta = consulta.where(DetalleAbastecimiento.producto_id == producto_id)
    if proveedor_id is not None:
        consulta = consulta.where(Abastecimiento.proveedor_id == proveedor_id)

    filas = db.execute(
        consulta.order_by(
            Abastecimiento.fecha.desc(), DetalleAbastecimiento.id.desc()
        ).limit(max(1, min(limite, 5000)))
    ).all()

    return [
        {
            "codigo": codigo,
            "producto": nombre,
            "proveedor": proveedor,
            "presentacion": presentacion,
            "cantidad": num(dec(cantidad)),
            "costo_unitario": num(q2(dec(costo_unitario))),
            "costo_transporte": num(q2(dec(costo_transporte or 0))),
            "subtotal": num(q2(dec(subtotal))),
            "factor": num(dec(factor)),
            "fecha": fecha.isoformat(),
            "documento": documento,
        }
        for (
            codigo,
            nombre,
            proveedor,
            presentacion,
            cantidad,
            costo_unitario,
            costo_transporte,
            subtotal,
            factor,
            fecha,
            documento,
        ) in filas
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
            UnidadMedida.nombre,
            Existencia.cantidad_base,
            Existencia.costo_promedio_base,
        )
        .join(Producto, Producto.id == Existencia.producto_id)
        .outerjoin(UnidadMedida, UnidadMedida.id == Producto.unidad_base_id)
        .where(*filtros)
    ).all()

    mapa_pres = _mapa_presentacion_principal(db, [f[0] for f in filas])
    resultado = []
    for id_, codigo, nombre, unidad_base, cantidad, costo in filas:
        cant_dec = dec(cantidad)
        valor = cant_dec * dec(costo)
        pres = mapa_pres.get(id_)
        factor = pres[1] if pres else Decimal("1")
        resultado.append(
            {
                "producto_id": id_,
                "codigo": codigo,
                "producto": nombre,
                "unidad_base": unidad_base,
                "presentacion_nombre": pres[0] if pres else None,
                "factor_base": num(factor),
                "cantidad_base": num(cant_dec),
                "cantidad_presentacion": num(q4(cant_dec / factor)),
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


def inventario_por_lote(
    db: Session,
    *,
    producto_id: int | None = None,
    almacen_id: int | None = None,
    solo_con_stock: bool = False,
    estado: str | None = None,
    limite: int = 500,
) -> list[dict[str, Any]]:
    """Inventario desglosado por lote: stock, costo y precio de cada uno."""
    from app.db.models import LoteInventario

    filtros = []
    if producto_id is not None:
        filtros.append(LoteInventario.producto_id == producto_id)
    if almacen_id is not None:
        filtros.append(LoteInventario.almacen_id == almacen_id)
    if solo_con_stock or estado == "con_stock":
        filtros.append(LoteInventario.cantidad_disponible > 0)
    elif estado == "agotado":
        filtros.append(LoteInventario.cantidad_disponible <= 0)

    filas = db.execute(
        select(
            LoteInventario.id,
            LoteInventario.codigo_lote,
            LoteInventario.fecha_ingreso,
            LoteInventario.cantidad_inicial,
            LoteInventario.cantidad_disponible,
            LoteInventario.costo_base,
            LoteInventario.costo_unitario,
            LoteInventario.costo_transporte,
            LoteInventario.precio_venta,
            LoteInventario.estado,
            LoteInventario.origen,
            Producto.codigo,
            Producto.nombre,
            UnidadMedida.nombre,
            PresentacionProducto.nombre,
            PresentacionProducto.factor_base,
            Proveedor.razon_social,
        )
        .join(Producto, Producto.id == LoteInventario.producto_id)
        .outerjoin(UnidadMedida, UnidadMedida.id == Producto.unidad_base_id)
        .outerjoin(
            PresentacionProducto,
            PresentacionProducto.id == LoteInventario.presentacion_principal_id,
        )
        .outerjoin(Proveedor, Proveedor.id == LoteInventario.proveedor_id)
        .where(*filtros)
        .order_by(Producto.nombre, LoteInventario.fecha_ingreso.asc().nulls_last(), LoteInventario.id)
        .limit(max(1, min(limite, 5000)))
    ).all()

    resultado = []
    for (
        lote_id,
        codigo_lote,
        fecha_ingreso,
        cantidad_inicial,
        cantidad_disponible,
        costo_base,
        costo_unitario,
        costo_transporte,
        precio_venta,
        estado_lote,
        origen,
        codigo,
        nombre,
        unidad_base_nombre,
        presentacion_nombre,
        factor_base,
        proveedor_nombre,
    ) in filas:
        cantidad = dec(cantidad_disponible)
        cantidad_ini = dec(cantidad_inicial)
        factor = dec(factor_base) if factor_base and dec(factor_base) > 0 else Decimal("1")
        unidades_lote = (cantidad_ini / factor) if factor > 0 else Decimal("0")
        transporte = dec(costo_transporte or 0)
        transporte_unitario = (
            q2(transporte / unidades_lote) if unidades_lote > 0 else Decimal("0")
        )
        resultado.append(
            {
                "lote_id": lote_id,
                "codigo_lote": codigo_lote,
                "fecha_ingreso": fecha_ingreso.isoformat() if fecha_ingreso else None,
                "producto_codigo": codigo,
                "producto_nombre": nombre,
                "unidad_base": unidad_base_nombre,
                "presentacion_nombre": presentacion_nombre,
                "factor_base": num(factor),
                "cantidad_inicial": num(q4(cantidad_ini)),
                "cantidad_disponible": num(q4(cantidad)),
                "cantidad_inicial_presentacion": num(q4(unidades_lote)),
                "cantidad_disponible_presentacion": num(q4(cantidad / factor)),
                "costo_base": num(dec(costo_base)),
                "costo_unitario": num(q2(dec(costo_unitario))),
                "costo_transporte": num(q2(transporte)),
                "costo_transporte_unitario": num(transporte_unitario),
                "precio_venta": num(q2(dec(precio_venta))),
                "valor_costo": num(q2(cantidad * dec(costo_base))),
                "proveedor_nombre": proveedor_nombre,
                "estado": "AGOTADO" if cantidad <= 0 else estado_lote,
                "origen": origen,
            }
        )
    return resultado


def ventas_por_lote(
    db: Session, *, desde: date | None = None, hasta: date | None = None, limite: int = 500
) -> list[dict[str, Any]]:
    """Ventas y rentabilidad por lote (se usa el costo del lote, no el promedio)."""
    from app.db.models import LoteInventario

    inicio, fin = _periodo(desde, hasta)
    filtros = []
    if desde is not None or hasta is not None:
        filtros.append(Venta.fecha.between(inicio, fin))

    filas = db.execute(
        select(
            LoteInventario.id,
            LoteInventario.codigo_lote,
            LoteInventario.costo_transporte,
            Producto.codigo,
            Producto.nombre,
            UnidadMedida.nombre,
            PresentacionProducto.nombre,
            PresentacionProducto.factor_base,
            func.coalesce(func.sum(DetalleVenta.cantidad_base), 0),
            func.coalesce(func.sum(DetalleVenta.subtotal), 0),
            func.coalesce(func.sum(DetalleVenta.costo_total_linea), 0),
        )
        .join(DetalleVenta, DetalleVenta.lote_id == LoteInventario.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .join(Producto, Producto.id == LoteInventario.producto_id)
        .outerjoin(UnidadMedida, UnidadMedida.id == Producto.unidad_base_id)
        .outerjoin(
            PresentacionProducto,
            PresentacionProducto.id == LoteInventario.presentacion_principal_id,
        )
        .where(Venta.estado == "CONFIRMADO", *filtros)
        .group_by(
            LoteInventario.id,
            LoteInventario.codigo_lote,
            LoteInventario.costo_transporte,
            Producto.codigo,
            Producto.nombre,
            UnidadMedida.nombre,
            PresentacionProducto.nombre,
            PresentacionProducto.factor_base,
        )
        .order_by(func.sum(DetalleVenta.subtotal).desc())
        .limit(max(1, min(limite, 5000)))
    ).all()

    resultado = []
    for (
        lote_id,
        codigo_lote,
        costo_transporte,
        codigo,
        nombre,
        unidad_base_nombre,
        presentacion_nombre,
        factor_base,
        cantidad,
        ingresos,
        costo,
    ) in filas:
        ingresos_dec = dec(ingresos)
        costo_dec = dec(costo)
        cantidad_dec = dec(cantidad)
        factor = dec(factor_base) if factor_base and dec(factor_base) > 0 else Decimal("1")
        resultado.append(
            {
                "lote_id": lote_id,
                "codigo_lote": codigo_lote,
                "producto_codigo": codigo,
                "producto_nombre": nombre,
                "unidad_base": unidad_base_nombre,
                "presentacion_nombre": presentacion_nombre,
                "factor_base": num(factor),
                "cantidad_base": num(q4(cantidad_dec)),
                "cantidad_presentacion": num(q4(cantidad_dec / factor)),
                "ingresos": num(q2(ingresos_dec)),
                "costo": num(q2(costo_dec)),
                "costo_transporte": num(q2(dec(costo_transporte or 0))),
                "utilidad_bruta": num(q2(ingresos_dec - costo_dec)),
            }
        )
    return resultado


def ganancias_por_proveedor(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    agrupar: str = "mes",
) -> list[dict[str, Any]]:
    """Histórico de ganancias por proveedor.

    Cada lote de inventario recuerda al proveedor que suministró la mercadería
    (`lotes_inventario.proveedor_id`). Con ese dato, lo que se vendió de cada
    lote se atribuye a su proveedor:

    - **compras**: lo que se le compró en el periodo (mercadería + transporte);
    - **ingresos**: lo que se vendió de su mercadería;
    - **costo**: el costo de lo vendido (con su transporte);
    - **margen**: ingresos − costo.

    Se agrupa por mes (o por el periodo completo) para ver la evolución.
    """
    from app.db.models import LoteInventario

    inicio, fin = _periodo(desde, hasta)
    por_mes = agrupar != "total"

    # --- Lo vendido, atribuido al proveedor del lote ------------------------
    if por_mes:
        periodo_ventas = func.date_trunc("month", Venta.fecha).cast(String).label("periodo")
        periodo_compras = (
            func.date_trunc("month", Abastecimiento.fecha).cast(String).label("periodo")
        )
    else:
        periodo_ventas = literal("total").label("periodo")
        periodo_compras = literal("total").label("periodo")

    ventas_filas = db.execute(
        select(
            LoteInventario.proveedor_id.label("proveedor_id"),
            periodo_ventas,
            func.coalesce(func.sum(DetalleVenta.subtotal), 0).label("ingresos"),
            func.coalesce(func.sum(DetalleVenta.costo_total_linea), 0).label("costo"),
            func.coalesce(func.sum(DetalleVenta.cantidad_base), 0).label("cantidad_base"),
            func.count(func.distinct(Venta.id)).label("operaciones"),
        )
        .join(DetalleVenta, DetalleVenta.lote_id == LoteInventario.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .where(Venta.estado == "CONFIRMADO", Venta.fecha.between(inicio, fin))
        .group_by(LoteInventario.proveedor_id, periodo_ventas)
    ).all()

    # --- Lo comprado a cada proveedor en el periodo -------------------------
    compras_filas = db.execute(
        select(
            Abastecimiento.proveedor_id.label("proveedor_id"),
            periodo_compras,
            func.coalesce(func.sum(DetalleAbastecimiento.subtotal), 0).label("compras"),
            func.coalesce(func.sum(DetalleAbastecimiento.costo_transporte), 0).label("transporte"),
            func.count(func.distinct(Abastecimiento.id)).label("ingresos_registrados"),
        )
        .join(DetalleAbastecimiento, DetalleAbastecimiento.abastecimiento_id == Abastecimiento.id)
        .where(Abastecimiento.estado == "CONFIRMADO", Abastecimiento.fecha.between(inicio, fin))
        .group_by(Abastecimiento.proveedor_id, periodo_compras)
    ).all()

    compras: dict[tuple[int | None, str], dict[str, Any]] = {}
    for proveedor_id, periodo, monto, transporte, registros in compras_filas:
        compras[(proveedor_id, periodo)] = {
            "compras": dec(monto),
            "transporte": dec(transporte),
            "registros": registros,
        }

    # --- Unir y calcular el margen ------------------------------------------
    filas: dict[tuple[int | None, str], dict[str, Any]] = {}
    for proveedor_id, periodo, ingresos, costo, cantidad, operaciones in ventas_filas:
        clave = (proveedor_id, periodo)
        filas[clave] = {
            "proveedor_id": proveedor_id,
            "periodo": periodo,
            "ingresos": dec(ingresos),
            "costo": dec(costo),
            "cantidad_base": dec(cantidad),
            "operaciones": operaciones,
        }
    for (proveedor_id, periodo), datos in compras.items():
        clave = (proveedor_id, periodo)
        if clave not in filas:
            filas[clave] = {
                "proveedor_id": proveedor_id,
                "periodo": periodo,
                "ingresos": Decimal("0"),
                "costo": Decimal("0"),
                "cantidad_base": Decimal("0"),
                "operaciones": 0,
            }
        filas[clave].update(datos)

    nombres = {
        id_: nombre
        for id_, nombre in db.execute(select(Proveedor.id, Proveedor.razon_social)).all()
    }

    resultado = []
    for (proveedor_id, periodo), datos in filas.items():
        ingresos = datos["ingresos"]
        costo = datos["costo"]
        margen = ingresos - costo
        porcentaje = (margen / ingresos * Decimal("100")) if ingresos else Decimal("0")
        compras_total = datos.get("compras", Decimal("0"))
        resultado.append(
            {
                "proveedor_id": proveedor_id,
                "proveedor": nombres.get(proveedor_id) if proveedor_id else "Sin proveedor",
                "periodo": periodo,
                "operaciones": datos["operaciones"],
                "compras": num(q2(compras_total)),
                "costo_transporte_compras": num(q2(datos.get("transporte", Decimal("0")))),
                "ingresos": num(q2(ingresos)),
                "costo": num(q2(costo)),
                "margen_bruto": num(q2(margen)),
                "margen_porcentaje": num(porcentaje.quantize(Decimal("0.01"))),
                "cantidad_base": num(q4(datos["cantidad_base"])),
            }
        )

    resultado.sort(key=lambda item: (item["proveedor"], item["periodo"]))
    return resultado


__all__ = [
    "abastecimientos_por_proveedor",
    "exportar_ventas_csv",
    "ganancias_por_proveedor",
    "historico_de_costos",
    "inventario_por_lote",
    "inventario_valorizado",
    "margen_bruto",
    "ventas_por_categoria",
    "ventas_por_lote",
    "ventas_por_periodo",
    "ventas_por_producto",
    "ventas_por_usuario",
]
