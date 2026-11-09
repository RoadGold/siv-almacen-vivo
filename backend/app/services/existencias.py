"""Servicios de consulta de existencias, kardex, radar y dashboard."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AjusteInventario,
    Almacen,
    Existencia,
    MovimientoInventario,
    PresentacionProducto,
    Producto,
    ProductoProveedor,
    Proveedor,
    TipoMovimiento,
    Venta,
)
from app.domain.unidades import ErrorNegocio, dec, num, q2, q4
from app.services import inventario
from app.services.secuencias import siguiente_numero


def _presentacion_visual(producto: Producto, cantidad_base: Decimal) -> PresentacionProducto | None:
    """Elige la presentaciÃ³n con la que se entiende mejor la cantidad actual."""
    activas = [p for p in producto.presentaciones if p.activo and p.es_venta]
    if not activas:
        return None
    candidatas = [p for p in activas if dec(p.factor_base) <= cantidad_base] if cantidad_base > 0 else []
    if candidatas:
        return max(candidatas, key=lambda p: dec(p.factor_base))
    return min(activas, key=lambda p: dec(p.factor_base))


def _cantidad_en_presentacion(cantidad_base: Decimal, presentacion: PresentacionProducto | None) -> str:
    if presentacion is None:
        return num(q4(cantidad_base))
    factor = dec(presentacion.factor_base)
    if factor == 0:
        return num(q4(cantidad_base))
    valor = cantidad_base / factor
    decimales = 3 if valor % 1 != 0 else 0
    return num(q4(valor).quantize(Decimal(1).scaleb(-decimales)))


def listar_existencias(
    db: Session,
    *,
    almacen_id: int | None = None,
    q: str | None = None,
    categoria_id: int | None = None,
    estado: str | None = None,
    pagina: int = 1,
    tamano: int = 25,
    sin_paginacion: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    pagina = max(1, pagina)
    tamano = max(1, min(tamano, 200)) if not sin_paginacion else max(1, tamano)

    filtros = []
    if almacen_id is not None:
        filtros.append(Existencia.almacen_id == almacen_id)
    if categoria_id is not None:
        filtros.append(Producto.categoria_id == categoria_id)

    # El estado se resuelve en el servidor para poder filtrar y paginar sin
    # cargar todo el catálogo en memoria.
    if estado == "agotado":
        filtros.append(Existencia.cantidad_base <= 0)
    elif estado == "bajo_minimo":
        filtros.append(Existencia.cantidad_base > 0)
        filtros.append(Existencia.cantidad_base < Producto.stock_minimo_base)
    elif estado == "disponible":
        filtros.append(Existencia.cantidad_base > 0)
        filtros.append(
            or_(
                Producto.stock_minimo_base <= 0,
                Existencia.cantidad_base >= Producto.stock_minimo_base,
            )
        )

    consulta = (
        select(Existencia, Producto, Almacen)
        .join(Producto, Producto.id == Existencia.producto_id)
        .join(Almacen, Almacen.id == Existencia.almacen_id)
        .where(*filtros)
        .order_by(Producto.nombre_normalizado, Producto.id, Existencia.almacen_id)
    )

    if q:
        texto = q.strip().lower()
        consulta = consulta.where(
            func.lower(Producto.nombre).like(f"%{texto}%")
            | (func.lower(Producto.codigo).like(f"%{texto}%"))
        )

    total = db.execute(
        select(func.count()).select_from(consulta.subquery())
    ).scalar_one()

    if sin_paginacion:
        filas = db.execute(consulta).all()
    else:
        filas = db.execute(consulta.offset((pagina - 1) * tamano).limit(tamano)).all()
    resultado: list[dict[str, Any]] = []

    for existencia, producto, almacen in filas:
        cantidad = dec(existencia.cantidad_base)
        minimo = dec(producto.stock_minimo_base)
        presentacion = _presentacion_visual(producto, cantidad)
        if cantidad <= 0:
            estado_producto = "agotado"
        elif minimo > 0 and cantidad < minimo:
            estado_producto = "bajo_minimo"
        else:
            estado_producto = "disponible"

        resultado.append(
            {
                "producto_id": producto.id,
                "almacen_id": almacen.id,
                "codigo": producto.codigo,
                "producto": producto.nombre,
                "categoria": producto.categoria.nombre if producto.categoria else None,
                "unidad_base": producto.unidad_base.nombre if producto.unidad_base else None,
                "cantidad_base": num(q4(cantidad)),
                "costo_promedio_base": num(existencia.costo_promedio_base),
                "valor_costo": num(q2(cantidad * dec(existencia.costo_promedio_base))),
                "stock_minimo_base": num(q4(minimo)),
                "presentacion_principal": presentacion.nombre if presentacion else None,
                "cantidad_presentacion": _cantidad_en_presentacion(cantidad, presentacion),
                "estado": estado_producto,
                "ubicacion": almacen.nombre,
            }
        )

    return resultado, total


def movimientos(
    db: Session,
    *,
    producto_id: int | None = None,
    almacen_id: int | None = None,
    tipo: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = 1,
    tamano: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    pagina = max(1, pagina)
    tamano = max(1, min(tamano, 200))

    filtros = []
    if producto_id is not None:
        filtros.append(MovimientoInventario.producto_id == producto_id)
    if almacen_id is not None:
        filtros.append(MovimientoInventario.almacen_id == almacen_id)
    if tipo:
        filtros.append(MovimientoInventario.tipo == tipo)
    if desde:
        filtros.append(func.date(MovimientoInventario.created_at) >= desde)
    if hasta:
        filtros.append(func.date(MovimientoInventario.created_at) <= hasta)

    total = db.execute(
        select(func.count()).select_from(MovimientoInventario).where(*filtros)
    ).scalar_one()

    filas = db.execute(
        select(MovimientoInventario, Producto, Almacen)
        .join(Producto, Producto.id == MovimientoInventario.producto_id)
        .join(Almacen, Almacen.id == MovimientoInventario.almacen_id)
        .where(*filtros)
        .order_by(MovimientoInventario.created_at.desc(), MovimientoInventario.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).all()

    resultado = []
    for movimiento, producto, almacen in filas:
        resultado.append(
            {
                "id": movimiento.id,
                "producto_id": movimiento.producto_id,
                "producto_codigo": producto.codigo,
                "producto_nombre": producto.nombre,
                "almacen_id": movimiento.almacen_id,
                "almacen": almacen.nombre,
                "tipo": movimiento.tipo.value,
                "cantidad_base_signed": num(q4(dec(movimiento.cantidad_base_signed))),
                "saldo_base_despues": num(q4(dec(movimiento.saldo_base_despues))),
                "costo_unitario_base": num(dec(movimiento.costo_unitario_base)),
                "origen_tipo": movimiento.origen_tipo,
                "origen_id": movimiento.origen_id,
                "referencia": movimiento.referencia,
                "usuario": producto_nombre_usuario(db, movimiento.usuario_id),
                "created_at": movimiento.created_at,
            }
        )
    return resultado, total


def producto_nombre_usuario(db: Session, usuario_id: int | None) -> str | None:
    if usuario_id is None:
        return None
    from app.db.models import Usuario

    usuario = db.get(Usuario, usuario_id)
    return usuario.nombre if usuario else None


def radar_reposicion(
    db: Session, *, almacen_id: int | None = None, limite: int = 50
) -> list[dict[str, Any]]:
    """Ordena productos por urgencia de reposiciÃ³n (plan Â§5.6)."""
    existencias, _ = listar_existencias(
        db, almacen_id=almacen_id, pagina=1, tamano=1, sin_paginacion=True
    )
    urgentes = [e for e in existencias if e["estado"] in ("agotado", "bajo_minimo")]
    # Se usa el listado completo (no paginado) para no perder productos urgentes.

    proveedores_por_producto: dict[int, list[tuple[int, str, str | None]]] = {}
    for vinculo, proveedor in db.execute(
        select(ProductoProveedor, Proveedor)
        .join(Proveedor, Proveedor.id == ProductoProveedor.proveedor_id)
        .where(Proveedor.activo.is_(True))
    ).all():
        proveedores_por_producto.setdefault(vinculo.producto_id, []).append(
            (proveedor.id, proveedor.razon_social, num(vinculo.ultimo_costo) if vinculo.ultimo_costo else None)
        )

    resultado = []
    for item in urgentes:
        lista = proveedores_por_producto.get(item["producto_id"], [])
        habitual = sorted(lista, key=lambda x: (x[2] is None, x[2] or ""), reverse=False)
        proveedor = habitual[0] if habitual else None
        resultado.append(
            {
                **item,
                "proveedor_id": proveedor[0] if proveedor else None,
                "proveedor_sugerido": proveedor[1] if proveedor else None,
                "ultimo_costo": proveedor[2] if proveedor else None,
                "prioridad": 0 if item["estado"] == "agotado" else 1,
            }
        )

    resultado.sort(key=lambda x: (x["prioridad"], dec(x["cantidad_base"])))
    return resultado[:limite]


def dashboard_resumen(db: Session, almacen_id: int | None = None) -> dict[str, Any]:
    hoy = date.today()
    inicio = datetime.combine(hoy, datetime.min.time(), tzinfo=timezone.utc)

    total_ventas = db.execute(
        select(func.coalesce(func.sum(Venta.total), 0)).where(
            Venta.fecha == hoy, Venta.estado == "CONFIRMADO"
        )
    ).scalar_one()
    cantidad_ventas = db.execute(
        select(func.count())
        .select_from(Venta)
        .where(Venta.fecha == hoy, Venta.estado == "CONFIRMADO")
    ).scalar_one()

    # Los indicadores se calculan con agregaciones en el servidor: así el
    # resumen es correcto con 10 000 productos y no se carga todo en memoria.
    filtros_stock = []
    if almacen_id is not None:
        filtros_stock.append(Existencia.almacen_id == almacen_id)

    agotados = db.execute(
        select(func.count())
        .select_from(Existencia)
        .where(*filtros_stock, Existencia.cantidad_base <= 0)
    ).scalar_one()
    bajo_minimo = db.execute(
        select(func.count())
        .select_from(Existencia)
        .join(Producto, Producto.id == Existencia.producto_id)
        .where(
            *filtros_stock,
            Existencia.cantidad_base > 0,
            Existencia.cantidad_base < Producto.stock_minimo_base,
        )
    ).scalar_one()
    valor = db.execute(
        select(func.coalesce(func.sum(Existencia.cantidad_base * Existencia.costo_promedio_base), 0)).where(
            *filtros_stock
        )
    ).scalar_one()
    total_productos = db.execute(
        select(func.count()).select_from(Producto).where(Producto.activo.is_(True))
    ).scalar_one()

    ultima_venta = db.execute(
        select(Venta).where(Venta.estado == "CONFIRMADO").order_by(Venta.id.desc()).limit(1)
    ).scalar_one_or_none()
    ultimo_ingreso = db.execute(
        select(func.max(MovimientoInventario.created_at)).where(
            MovimientoInventario.tipo == TipoMovimiento.ABASTECIMIENTO
        )
    ).scalar_one_or_none()

    return {
        "fecha": hoy.isoformat(),
        "ventas_dia": num(q2(dec(total_ventas))),
        "cantidad_ventas_dia": cantidad_ventas,
        "ingresos_dia": "0",
        "productos_agotados": agotados,
        "productos_bajo_minimo": bajo_minimo,
        "valor_inventario_costo": num(q2(valor)),
        "total_productos": total_productos,
        "ultimo_ingreso": ultimo_ingreso.isoformat() if ultimo_ingreso else None,
        "ultima_venta": ultima_venta.numero if ultima_venta else None,
    }


def crear_ajuste(
    db: Session,
    *,
    almacen_id: int,
    producto_id: int,
    cantidad_base: Decimal,
    motivo: str,
    usuario_id: int,
) -> AjusteInventario:
    """Ajuste administrativo: suma o resta stock con motivo documentado."""
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise ErrorNegocio("El producto no existe.")
    cantidad = dec(cantidad_base)
    if cantidad == 0:
        raise ErrorNegocio("El ajuste debe ser distinto de cero.")

    ajuste = AjusteInventario(
        numero="PENDIENTE",
        almacen_id=almacen_id,
        producto_id=producto_id,
        tipo=TipoMovimiento.AJUSTE_ADMINISTRATIVO,
        cantidad_base=q4(cantidad),
        motivo=motivo,
        estado="CONFIRMADO",
        usuario_id=usuario_id,
    )
    db.add(ajuste)
    db.flush()
    ajuste.numero = siguiente_numero(db, "AJUSTE", almacen_id)

    if cantidad > 0:
        existencia = inventario.bloquear_existencia(db, almacen_id, producto_id)
        inventario.aplicar_entrada(
            db,
            almacen_id=almacen_id,
            producto_id=producto_id,
            cantidad_base=cantidad,
            costo_unitario_base=dec(existencia.costo_promedio_base),
            tipo=TipoMovimiento.AJUSTE_ADMINISTRATIVO,
            origen_tipo="AJUSTE",
            origen_id=ajuste.id,
            usuario_id=usuario_id,
            referencia=ajuste.numero,
        )
    else:
        inventario.aplicar_salida(
            db,
            almacen_id=almacen_id,
            producto_id=producto_id,
            cantidad_base=-cantidad,
            tipo=TipoMovimiento.AJUSTE_ADMINISTRATIVO,
            origen_tipo="AJUSTE",
            origen_id=ajuste.id,
            usuario_id=usuario_id,
            referencia=ajuste.numero,
        )
    db.flush()
    return ajuste


def Ficha_producto(db: Session, producto_id: int) -> dict[str, Any]:
    """Ficha viva del producto: existencias, proveedores y huella reciente."""
    from app.db.models import Abastecimiento, DetalleAbastecimiento

    producto = db.execute(
        select(Producto)
        .options(
            selectinload(Producto.presentaciones),
            selectinload(Producto.categoria),
            selectinload(Producto.marca),
            selectinload(Producto.unidad_base),
        )
        .where(Producto.id == producto_id)
    ).scalar_one_or_none()
    if producto is None:
        raise ErrorNegocio("El producto no existe.")

    existencias = []
    for ex in db.execute(
        select(Existencia, Almacen).join(Almacen, Almacen.id == Existencia.almacen_id)
        .where(Existencia.producto_id == producto_id)
    ).all():
        cantidad = dec(ex.cantidad_base)
        presentacion = _presentacion_visual(producto, cantidad)
        existencias.append(
            {
                "almacen_id": ex.almacen.id,
                "almacen": ex.almacen.nombre,
                "cantidad_base": num(q4(cantidad)),
                "costo_promedio_base": num(ex.costo_promedio_base),
                "presentacion_principal": presentacion.nombre if presentacion else None,
                "cantidad_presentacion": _cantidad_en_presentacion(cantidad, presentacion),
                "unidad_base": producto.unidad_base.nombre if producto.unidad_base else None,
            }
        )

    proveedores = []
    for vinculo, proveedor in db.execute(
        select(ProductoProveedor, Proveedor)
        .join(Proveedor, Proveedor.id == ProductoProveedor.proveedor_id)
        .where(ProductoProveedor.producto_id == producto_id)
    ).all():
        proveedores.append(
            {
                "proveedor_id": proveedor.id,
                "proveedor": proveedor.razon_social,
                "habitual": vinculo.habitual,
                "ultimo_costo": num(vinculo.ultimo_costo) if vinculo.ultimo_costo else None,
                "ultima_fecha_compra": (
                    vinculo.ultima_fecha_compra.isoformat()
                    if vinculo.ultima_fecha_compra
                    else None
                ),
            }
        )

    ultimos, _ = movimientos(db, producto_id=producto_id, pagina=1, tamano=20)
    ultimo_costo = None
    row = db.execute(
        select(DetalleAbastecimiento.costo_unitario)
        .join(Abastecimiento, Abastecimiento.id == DetalleAbastecimiento.abastecimiento_id)
        .where(
            DetalleAbastecimiento.producto_id == producto_id,
            Abastecimiento.estado == "CONFIRMADO",
        )
        .order_by(Abastecimiento.fecha.desc(), DetalleAbastecimiento.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is not None:
        ultimo_costo = num(row)

    from app.services.catalogo import producto_a_dict

    base = producto_a_dict(producto)
    base["existencias"] = existencias
    base["proveedores"] = proveedores
    base["ultimo_costo"] = ultimo_costo
    base["movimientos_recientes"] = ultimos
    return base


def registrar_saldo_inicial(
    db: Session,
    *,
    almacen_id: int,
    lineas: list[dict[str, Any]],
    usuario_id: int,
    referencia: str = "Inventario inicial",
) -> dict[str, Any]:
    """Carga inicial de existencias: una operación administrativa, no una compra.

    Se diferencia de un abastecimiento (que exige proveedor) y queda registrada
    con el tipo de movimiento `SALDO_INICIAL`.
    """
    if not lineas:
        raise ErrorNegocio("Debe incluir al menos una línea de inventario inicial.")
    total = Decimal("0")
    detalle = []
    for linea in lineas:
        producto = db.get(Producto, linea["producto_id"])
        if producto is None:
            raise ErrorNegocio("El producto de una línea no existe.")
        cantidad = dec(linea["cantidad_base"])
        if cantidad <= 0:
            raise ErrorNegocio("La cantidad del inventario inicial debe ser mayor que cero.")
        costo = dec(linea.get("costo_unitario_base") or 0)
        existencia = inventario.bloquear_existencia(db, almacen_id, producto.id)
        if dec(existencia.cantidad_base) != 0:
            raise ErrorNegocio(
                f"«{producto.nombre}» ya tiene existencias: use un ajuste administrativo.",
                detalle={"producto_id": producto.id},
            )
        inventario.aplicar_entrada(
            db,
            almacen_id=almacen_id,
            producto_id=producto.id,
            cantidad_base=cantidad,
            costo_unitario_base=costo,
            tipo=TipoMovimiento.SALDO_INICIAL,
            origen_tipo="INVENTARIO_INICIAL",
            origen_id=0,
            usuario_id=usuario_id,
            referencia=referencia,
        )
        total += cantidad
        detalle.append(
            {
                "producto_id": producto.id,
                "producto": producto.nombre,
                "cantidad_base": num(q4(cantidad)),
                "costo_unitario_base": num(costo),
            }
        )
    db.flush()
    return {"total_unidades_base": num(q4(total)), "lineas": detalle}


__all__ = [
    "crear_ajuste",
    "dashboard_resumen",
    "ficha_producto",
    "listar_existencias",
    "movimientos",
    "radar_reposicion",
    "registrar_saldo_inicial",
]

