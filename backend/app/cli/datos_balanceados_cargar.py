"""Carga el catálogo inicial de balanceados (VITAMAXPRO/INVITA y TOMASINO).

Uso:
    python -m app.cli.datos_balanceados_cargar --simular
    python -m app.cli.datos_balanceados_cargar

Crea:
- Los dos proveedores (VITAMAXPRO y TOMASINO).
- Las categorías y marcas que hagan falta.
- Los 161 productos con sus 189 presentaciones (empaques), con el costo del
  distribuidor como costo de referencia y el precio de venta calculado con el
  margen.

Es idempotente: si el código del producto ya existe, no lo duplica; solo
actualiza sus datos. Por eso se puede volver a ejecutar sin riesgo.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal


def _preparar_consola() -> None:
    """Evita errores de codificación en la consola de Windows (cp1252)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


_preparar_consola()

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.cli.datos_balanceados import Item, precio_venta_de
from app.cli.traducir_balanceados import todos_los_items
from app.db.models import Categoria, Marca, Producto, Proveedor, UnidadMedida
from app.db.session import SessionLocal
from app.domain.unidades import dec
from app.services import catalogo

#: Datos de los proveedores que se crean.
PROVEEDORES = {
    "VITAMAXPRO": {
        "codigo": "PRV-VMP",
        "razon_social": "Vitamaxpro",
        "nombre_comercial": "Vitamaxpro",
        "contacto": "Distribuidor de balanceados",
    },
    "TOMASINO": {
        "codigo": "PRV-TOM",
        "razon_social": "Tomasino",
        "nombre_comercial": "Tomasino",
        "contacto": "Distribuidor de balanceados",
    },
}


def _obtener_crear_categoria(db: Session, nombre: str) -> Categoria:
    """Busca la categoría o la crea."""
    categoria = db.execute(
        select(Categoria).where(func.lower(Categoria.nombre) == nombre.strip().lower())
    ).scalar_one_or_none()
    if categoria is None:
        categoria = Categoria(nombre=nombre.strip())
        db.add(categoria)
        db.flush()
    return categoria


def _obtener_crear_marca(db: Session, nombre: str) -> Marca:
    """Busca la marca o la crea."""
    marca = db.execute(
        select(Marca).where(func.lower(Marca.nombre) == nombre.strip().lower())
    ).scalar_one_or_none()
    if marca is None:
        marca = Marca(nombre=nombre.strip())
        db.add(marca)
        db.flush()
    return marca


def _obtener_crear_proveedor(db: Session, clave: str) -> Proveedor:
    """Busca el proveedor o lo crea."""
    datos = PROVEEDORES[clave]
    proveedor = db.execute(
        select(Proveedor).where(
            func.lower(Proveedor.codigo) == datos["codigo"].lower()
        )
    ).scalar_one_or_none()
    if proveedor is None:
        proveedor = Proveedor(
            codigo=datos["codigo"],
            razon_social=datos["razon_social"],
            nombre_comercial=datos["nombre_comercial"],
            contacto=datos["contacto"],
            ruc=None,
            telefono=None,
            direccion=None,
            email=None,
            observaciones=None,
            activo=True,
        )
        db.add(proveedor)
        db.flush()
    return proveedor


def _presentaciones_de(item: Item) -> list[dict]:
    """Las presentaciones del producto, con su precio de venta."""
    presentaciones = []
    for empaque in item.empaques:
        presentaciones.append(
            {
                "nombre": empaque.nombre,
                "factor_base": str(empaque.factor_base),
                "precio_venta": precio_venta_de(empaque.precio_costo),
                "costo_referencia": empaque.precio_costo,
                "codigo_barras": None,
                "es_compra": True,
                "es_venta": True,
                # Se vende a granel (por kilo), así que admite fracciones.
                "permite_fraccion": True,
            }
        )
    return presentaciones


def cargar(db: Session, simular: bool = False) -> dict[str, int]:
    """Carga el catálogo. Devuelve un resumen de lo hecho."""
    items = todos_los_items()

    if simular:
        return {
            "productos": len(items),
            "empaques": sum(len(item.empaques) for item in items),
            "categorias": len({item.categoria for item in items}),
            "marcas": len({item.marca for item in items}),
            "nuevos": 0,
            "actualizados": 0,
        }

    # --- Unidades ---------------------------------------------------------
    unidad = db.execute(
        select(UnidadMedida).where(UnidadMedida.codigo == "GR")
    ).scalar_one_or_none()
    if unidad is None:
        raise RuntimeError(
            "No está registrada la unidad GR. Ejecute primero: "
            "python -m app.cli.instalar --usuario admin --password clave"
        )

    # --- Proveedores ------------------------------------------------------
    proveedores = {clave: _obtener_crear_proveedor(db, clave) for clave in PROVEEDORES}

    nuevos = 0
    actualizados = 0

    for item in items:
        categoria = _obtener_crear_categoria(db, item.categoria)
        marca = _obtener_crear_marca(db, item.marca)

        # La identidad del producto depende del distribuidor:
        # - TOMASINO da un código por producto: ese código es su identidad.
        # - VITAMAXPRO no da código: la identidad es marca + nombre.
        #
        # Así, dos productos de TOMASINO con el mismo nombre («Broiler Tech
        # Nutrition» de 20 kg y de 40 kg) no se confunden, y los de VITAMAXPRO
        # conservan su código aunque la lista de precios cambie de tamaño.
        existente = None
        if item.codigo:
            existente = db.execute(
                select(Producto).where(
                    func.lower(Producto.codigo) == item.codigo.lower()
                )
            ).scalar_one_or_none()
        else:
            existente = db.execute(
                select(Producto)
                .join(Marca, Producto.marca_id == Marca.id)
                .where(
                    func.lower(Marca.nombre) == item.marca.lower(),
                    func.lower(Producto.nombre) == item.nombre.lower(),
                )
                .order_by(Producto.id)
            ).scalars().first()

        if existente is not None:
            # Ya existe: se actualizan los datos y se recargan las
            # presentaciones (se reemplazan las que tengan el mismo nombre).
            catalogo.actualizar_producto(
                db,
                existente.id,
                {
                    "nombre": item.nombre,
                    "categoria_id": categoria.id,
                    "marca_id": marca.id,
                    "activo": True,
                },
            )
            _recargar_presentaciones(db, existente, item)
            _vincular_proveedor(db, existente, proveedores[item.proveedor], item)
            actualizados += 1
            continue

        codigo = item.codigo or _siguiente_codigo(db, item.marca)
        producto = catalogo.crear_producto(
            db,
            {
                "codigo": codigo,
                "nombre": item.nombre,
                "descripcion": item.nota or None,
                "categoria_id": categoria.id,
                "marca_id": marca.id,
                "unidad_base_id": unidad.id,
                "stock_minimo_base": "0",
                "permite_fraccion": True,
                "activo": True,
                "presentaciones": _presentaciones_de(item),
            },
        )
        _vincular_proveedor(db, producto, proveedores[item.proveedor], item)
        nuevos += 1

    desactivados = _desactivar_sobrantes(db, items)

    db.commit()

    return {
        "productos": len(items),
        "empaques": sum(len(item.empaques) for item in items),
        "categorias": len({item.categoria for item in items}),
        "marcas": len({item.marca for item in items}),
        "nuevos": nuevos,
        "actualizados": actualizados,
        "desactivados": desactivados,
    }


def _siguiente_codigo(db: Session, marca: str) -> str:
    """El siguiente código libre para un producto de VITAMAXPRO o INVITA.

    Se numeran del 1 en adelante y no se reutiliza ningún número, aunque el
    producto se desactive después.
    """
    prefijo = "INV" if marca == "Invita" else "VMP"
    existentes = db.execute(
        select(Producto.codigo).where(Producto.codigo.ilike(f"{prefijo}-%"))
    ).scalars().all()

    usados = set()
    for codigo in existentes:
        try:
            usados.add(int(codigo.split("-")[-1]))
        except ValueError:
            continue

    numero = 1
    while numero in usados:
        numero += 1
    return f"{prefijo}-{numero:03d}"


def _desactivar_sobrantes(db: Session, items: list[Item]) -> int:
    """Desactiva los productos del catálogo que ya no están en la lista.

    Si se corrige la lista de precios y un producto desaparece, no se borra:
    se desactiva, para no romper el historial de compras y ventas.

    La comparación sigue la identidad de cada producto: por **código** para
    los de TOMASINO (que lo traen del distribuidor) y por **marca + nombre**
    para los de VITAMAXPRO (que no tienen código).
    """
    presentes_por_codigo = {item.codigo.lower() for item in items if item.codigo}
    presentes_por_nombre = {
        (item.marca.lower(), item.nombre.lower())
        for item in items
        if not item.codigo
    }

    # Solo se miran los productos de las marcas de balanceados: los demás
    # (arroz, gaseosa…) no se tocan.
    marcas_balanceados = {item.marca.lower() for item in items}
    candidatos = db.execute(
        select(Producto)
        .join(Marca, Producto.marca_id == Marca.id)
        .where(func.lower(Marca.nombre).in_(marcas_balanceados))
    ).scalars().all()

    desactivados = 0
    for producto in candidatos:
        if producto.codigo.lower() in presentes_por_codigo:
            continue
        clave = (producto.marca.nombre.lower(), producto.nombre.lower())
        if clave in presentes_por_nombre:
            continue
        producto.activo = False
        for presentacion in producto.presentaciones:
            presentacion.activo = False
        desactivados += 1

    db.flush()
    return desactivados


def _recargar_presentaciones(db: Session, producto: Producto, item: Item) -> None:
    """Deja las presentaciones del producto como deben estar.

    Las que ya existen se actualizan (precio o empaque); las que sobran se
    desactivan, para no romper el historial de ventas.
    """
    from app.db.models import PresentacionProducto

    deseadas = {empaque.nombre: empaque for empaque in item.empaques}

    for presentacion in list(producto.presentaciones):
        empaque = deseadas.pop(presentacion.nombre, None)
        if empaque is None:
            # Ya no se ofrece: se desactiva, no se borra.
            presentacion.activo = False
            continue
        presentacion.factor_base = dec(empaque.factor_base)
        presentacion.precio_venta = dec(precio_venta_de(empaque.precio_costo))
        presentacion.costo_referencia = dec(empaque.precio_costo)
        presentacion.es_compra = True
        presentacion.es_venta = True
        presentacion.permite_fraccion = True
        presentacion.activo = True

    for empaque in deseadas.values():
        producto.presentaciones.append(
            PresentacionProducto(
                nombre=empaque.nombre,
                factor_base=dec(empaque.factor_base),
                precio_venta=dec(precio_venta_de(empaque.precio_costo)),
                costo_referencia=dec(empaque.precio_costo),
                codigo_barras=None,
                es_compra=True,
                es_venta=True,
                permite_fraccion=True,
                activo=True,
            )
        )

    db.flush()


def _vincular_proveedor(
    db: Session, producto: Producto, proveedor: Proveedor, item: Item
) -> None:
    """Vincula el producto con su proveedor y el empaque con que se compra."""
    from app.db.models import ProductoProveedor

    vinculo = db.execute(
        select(ProductoProveedor).where(
            ProductoProveedor.producto_id == producto.id,
            ProductoProveedor.proveedor_id == proveedor.id,
        )
    ).scalar_one_or_none()

    presentacion = next(
        (
            p
            for p in producto.presentaciones
            if p.nombre == item.empaque_de_compra
        ),
        None,
    )

    if vinculo is None:
        vinculo = ProductoProveedor(
            producto_id=producto.id,
            proveedor_id=proveedor.id,
            habitual=True,
            presentacion_id=presentacion.id if presentacion else None,
            observacion=item.nota or None,
        )
        db.add(vinculo)
    else:
        vinculo.habitual = True
        vinculo.presentacion_id = presentacion.id if presentacion else None
        vinculo.observacion = item.nota or None

    db.flush()


def main() -> int:
    analizador = argparse.ArgumentParser(description="Carga el catálogo de balanceados.")
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Muestra lo que se cargaría sin escribir nada.",
    )
    argumentos = analizador.parse_args()

    if argumentos.simular:
        items = todos_los_items()
        print("SIMULACIÓN (no se escribe nada)")
        print(f"  Productos: {len(items)}")
        print(f"  Empaques (presentaciones): {sum(len(i.empaques) for i in items)}")
        print(f"  Categorías: {len({i.categoria for i in items})}")
        print(f"  Marcas: {len({i.marca for i in items})}")
        print(f"  Proveedores: {', '.join(PROVEEDORES)}")
        print(f"  Margen sobre el costo: {int(Decimal('0.30') * 100)}%")
        return 0

    db = SessionLocal()
    try:
        resumen = cargar(db)
    finally:
        db.close()

    print("Catálogo de balanceados cargado:")
    print(f"  Productos nuevos: {resumen['nuevos']}")
    print(f"  Productos actualizados: {resumen['actualizados']}")
    print(f"  Productos desactivados (ya no están en la lista): {resumen['desactivados']}")
    print(f"  Empaques (presentaciones): {resumen['empaques']}")
    print(f"  Categorías: {resumen['categorias']}")
    print(f"  Marcas: {resumen['marcas']}")
    print("  Precios de venta: costo + 30 %")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
