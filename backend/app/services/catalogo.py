"""Servicios de catálogo: unidades, categorías, marcas, productos y presentaciones."""

from __future__ import annotations

import unicodedata
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Categoria,
    Marca,
    PresentacionProducto,
    Producto,
    ProductoProveedor,
    UnidadMedida,
)
from app.domain.unidades import ErrorNegocio, dec, num


def normalizar(texto: str) -> str:
    """Minúsculas sin acentos, para búsquedas tolerantes a diferencias de escritura."""
    descompuesto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").strip()


def _verificar_codigo_unico(db: Session, codigo: str, producto_id: int | None = None) -> None:
    stmt = select(Producto).where(func.lower(Producto.codigo) == codigo.strip().lower())
    if producto_id is not None:
        stmt = stmt.where(Producto.id != producto_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise ErrorNegocio(
            f"Ya existe un producto con el código «{codigo}».",
            detalle={"campo": "codigo"},
        )


def _verificar_codigo_barras(
    db: Session, codigo_barras: str | None, presentacion_id: int | None = None
) -> None:
    if not codigo_barras:
        return
    limpio = codigo_barras.strip()
    if not limpio:
        return
    stmt = select(PresentacionProducto).where(
        PresentacionProducto.codigo_barras == limpio
    )
    if presentacion_id is not None:
        stmt = stmt.where(PresentacionProducto.id != presentacion_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise ErrorNegocio(
            f"El código de barras «{limpio}» ya está registrado en otra presentación.",
            detalle={"campo": "codigo_barras"},
        )


def producto_a_dict(producto: Producto, warehouse_id: int | None = None) -> dict[str, Any]:
    return {
        "id": producto.id,
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "categoria_id": producto.categoria_id,
        "categoria": producto.categoria.nombre if producto.categoria else None,
        "marca_id": producto.marca_id,
        "marca": producto.marca.nombre if producto.marca else None,
        "unidad_base_id": producto.unidad_base_id,
        "unidad_base": producto.unidad_base.nombre if producto.unidad_base else None,
        "stock_minimo_base": num(producto.stock_minimo_base),
        "permite_fraccion": producto.permite_fraccion,
        "activo": producto.activo,
        "created_at": producto.created_at,
        "presentaciones": [
            presentacion_a_dict(p) for p in sorted(producto.presentaciones, key=lambda x: x.id)
        ],
    }


def presentacion_a_dict(p: PresentacionProducto) -> dict[str, Any]:
    return {
        "id": p.id,
        "producto_id": p.producto_id,
        "nombre": p.nombre,
        "factor_base": num(p.factor_base),
        "precio_venta": num(p.precio_venta),
        "costo_referencia": num(p.costo_referencia),
        "codigo_barras": p.codigo_barras,
        "es_compra": p.es_compra,
        "es_venta": p.es_venta,
        "permite_fraccion": p.permite_fraccion,
        "activo": p.activo,
    }


def obtener_producto(db: Session, producto_id: int) -> Producto:
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
        raise ErrorNegocio("El producto no existe.", detalle={"producto_id": producto_id})
    return producto


def listar_productos(
    db: Session,
    *,
    q: str | None = None,
    categoria_id: int | None = None,
    marca_id: int | None = None,
    activo: bool | None = True,
    pagina: int = 1,
    tamano: int = 20,
    almacen_id: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Listado paginado con búsqueda tolerante (plan §5.1)."""
    pagina = max(1, pagina)
    tamano = max(1, min(tamano, 200))

    filtros = []
    if activo is not None:
        filtros.append(Producto.activo.is_(activo))
    if categoria_id is not None:
        filtros.append(Producto.categoria_id == categoria_id)
    if marca_id is not None:
        filtros.append(Producto.marca_id == marca_id)

    total = db.execute(
        select(func.count()).select_from(Producto).where(*filtros)
    ).scalar_one()

    consulta = (
        select(Producto)
        .options(
            selectinload(Producto.presentaciones),
            selectinload(Producto.categoria),
            selectinload(Producto.marca),
            selectinload(Producto.unidad_base),
        )
        .where(*filtros)
    )

    if q:
        texto = q.strip()
        patron = f"%{normalizar(texto)}%"
        condiciones = [
            Producto.nombre_normalizado.like(patron),
            func.lower(Producto.codigo).like(f"%{texto.lower()}%"),
            func.lower(Producto.descripcion).like(f"%{texto.lower()}%"),
        ]
        consulta = consulta.where(or_(*condiciones))
        total = db.execute(
            select(func.count())
            .select_from(Producto)
            .where(*filtros)
            .where(or_(*condiciones))
        ).scalar_one()

    consulta = (
        consulta.order_by(Producto.nombre_normalizado)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    productos = db.execute(consulta).scalars().all()
    return [producto_a_dict(p, almacen_id) for p in productos], total


def crear_producto(db: Session, datos: dict[str, Any]) -> Producto:
    codigo = datos["codigo"].strip()
    nombre = datos["nombre"].strip()
    _verificar_codigo_unico(db, codigo)

    unidad = db.get(UnidadMedida, datos["unidad_base_id"])
    if unidad is None:
        raise ErrorNegocio("La unidad base indicada no existe.", detalle={"campo": "unidad_base_id"})

    producto = Producto(
        codigo=codigo,
        nombre=nombre,
        nombre_normalizado=normalizar(nombre),
        descripcion=datos.get("descripcion"),
        categoria_id=datos.get("categoria_id"),
        marca_id=datos.get("marca_id"),
        unidad_base_id=unidad.id,
        stock_minimo_base=dec(datos.get("stock_minimo_base") or 0),
        permite_fraccion=bool(datos.get("permite_fraccion")),
        activo=bool(datos.get("activo", True)),
    )
    db.add(producto)
    db.flush()

    for pres in datos.get("presentaciones") or []:
        _verificar_codigo_barras(db, pres.get("codigo_barras"))
        producto.presentaciones.append(
            PresentacionProducto(
                nombre=pres["nombre"].strip(),
                factor_base=dec(pres["factor_base"]),
                precio_venta=dec(pres.get("precio_venta") or 0),
                costo_referencia=dec(pres.get("costo_referencia") or 0),
                codigo_barras=(pres.get("codigo_barras") or "").strip() or None,
                es_compra=bool(pres.get("es_compra", True)),
                es_venta=bool(pres.get("es_venta", True)),
                permite_fraccion=bool(pres.get("permite_fraccion", False)),
                activo=True,
            )
        )
    db.flush()
    return producto


def actualizar_producto(db: Session, producto_id: int, cambios: dict[str, Any]) -> Producto:
    producto = obtener_producto(db, producto_id)
    if "nombre" in cambios and cambios["nombre"]:
        producto.nombre = cambios["nombre"].strip()
        producto.nombre_normalizado = normalizar(producto.nombre)
    if "descripcion" in cambios:
        producto.descripcion = cambios["descripcion"]
    if "categoria_id" in cambios:
        producto.categoria_id = cambios["categoria_id"]
    if "marca_id" in cambios:
        producto.marca_id = cambios["marca_id"]
    if "stock_minimo_base" in cambios and cambios["stock_minimo_base"] is not None:
        producto.stock_minimo_base = dec(cambios["stock_minimo_base"])
    if "permite_fraccion" in cambios and cambios["permite_fraccion"] is not None:
        producto.permite_fraccion = bool(cambios["permite_fraccion"])
    if "activo" in cambios and cambios["activo"] is not None:
        producto.activo = bool(cambios["activo"])
    db.flush()
    return producto


def crear_presentacion(db: Session, producto_id: int, datos: dict[str, Any]) -> PresentacionProducto:
    producto = obtener_producto(db, producto_id)
    _verificar_codigo_barras(db, datos.get("codigo_barras"))
    nombre = datos["nombre"].strip()
    existe = db.execute(
        select(PresentacionProducto).where(
            PresentacionProducto.producto_id == producto_id,
            func.lower(PresentacionProducto.nombre) == nombre.lower(),
        )
    ).scalar_one_or_none()
    if existe is not None:
        raise ErrorNegocio(
            "El producto ya tiene una presentación con ese nombre.",
            detalle={"campo": "nombre"},
        )
    presentacion = PresentacionProducto(
        producto_id=producto_id,
        nombre=nombre,
        factor_base=dec(datos["factor_base"]),
        precio_venta=dec(datos.get("precio_venta") or 0),
        costo_referencia=dec(datos.get("costo_referencia") or 0),
        codigo_barras=(datos.get("codigo_barras") or "").strip() or None,
        es_compra=bool(datos.get("es_compra", True)),
        es_venta=bool(datos.get("es_venta", True)),
        permite_fraccion=bool(datos.get("permite_fraccion", False)),
        activo=True,
    )
    db.add(presentacion)
    db.flush()
    producto = obtener_producto(db, producto_id)
    return presentacion


def actualizar_presentacion(
    db: Session, presentacion_id: int, cambios: dict[str, Any]
) -> PresentacionProducto:
    presentacion = db.get(PresentacionProducto, presentacion_id)
    if presentacion is None:
        raise ErrorNegocio("La presentación no existe.")
    if "codigo_barras" in cambios:
        _verificar_codigo_barras(db, cambios["codigo_barras"], presentacion_id)
        presentacion.codigo_barras = (cambios["codigo_barras"] or "").strip() or None
    if "nombre" in cambios and cambios["nombre"]:
        presentacion.nombre = cambios["nombre"].strip()
    if "factor_base" in cambios and cambios["factor_base"] is not None:
        presentacion.factor_base = dec(cambios["factor_base"])
    if "precio_venta" in cambios and cambios["precio_venta"] is not None:
        presentacion.precio_venta = dec(cambios["precio_venta"])
    if "costo_referencia" in cambios and cambios["costo_referencia"] is not None:
        presentacion.costo_referencia = dec(cambios["costo_referencia"])
    for campo in ("es_compra", "es_venta", "permite_fraccion", "activo"):
        if campo in cambios and cambios[campo] is not None:
            setattr(presentacion, campo, bool(cambios[campo]))
    db.flush()
    return presentacion


def desactivar_presentacion(db: Session, presentacion_id: int) -> PresentacionProducto:
    presentacion = db.get(PresentacionProducto, presentacion_id)
    if presentacion is None:
        raise ErrorNegocio("La presentación no existe.")
    presentacion.activo = False
    db.flush()
    return presentacion


def listar_unidades(db: Session) -> list[UnidadMedida]:
    return list(db.execute(select(UnidadMedida).order_by(UnidadMedida.nombre)).scalars().all())


def crear_unidad(db: Session, datos: dict[str, Any]) -> UnidadMedida:
    codigo = datos["codigo"].strip().upper()
    existe = db.execute(
        select(UnidadMedida).where(func.lower(UnidadMedida.codigo) == codigo.lower())
    ).scalar_one_or_none()
    if existe is not None:
        raise ErrorNegocio("Ya existe una unidad de medida con ese código.")
    unidad = UnidadMedida(
        codigo=codigo,
        nombre=datos["nombre"].strip(),
        dimension=datos["dimension"],
        paso_minimo=int(datos.get("paso_minimo") or 1),
    )
    db.add(unidad)
    db.flush()
    return unidad


def listar_categorias(db: Session) -> list[Categoria]:
    return list(
        db.execute(select(Categoria).order_by(Categoria.nombre)).scalars().all()
    )


def crear_categoria(db: Session, nombre: str) -> Categoria:
    categoria = Categoria(nombre=nombre.strip())
    db.add(categoria)
    db.flush()
    return categoria


def listar_marcas(db: Session) -> list[Marca]:
    return list(db.execute(select(Marca).order_by(Marca.nombre)).scalars().all())


def crear_marca(db: Session, nombre: str) -> Marca:
    marca = Marca(nombre=nombre.strip())
    db.add(marca)
    db.flush()
    return marca


def buscar_por_codigo_barras(db: Session, codigo: str) -> PresentacionProducto | None:
    return db.execute(
        select(PresentacionProducto).where(
            PresentacionProducto.codigo_barras == codigo.strip()
        )
    ).scalar_one_or_none()


def proveedor_habitual(db: Session, producto_id: int, proveedor_id: int) -> ProductoProveedor | None:
    return db.execute(
        select(ProductoProveedor).where(
            ProductoProveedor.producto_id == producto_id,
            ProductoProveedor.proveedor_id == proveedor_id,
        )
    ).scalar_one_or_none()


__all__ = [
    "actualizar_presentacion",
    "actualizar_producto",
    "buscar_por_codigo_barras",
    "crear_categoria",
    "crear_marca",
    "crear_presentacion",
    "crear_producto",
    "crear_unidad",
    "desactivar_presentacion",
    "listar_categorias",
    "listar_marcas",
    "listar_productos",
    "listar_unidades",
    "normalizar",
    "obtener_producto",
    "presentacion_a_dict",
    "producto_a_dict",
]

