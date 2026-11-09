"""Generador del conjunto de datos de prueba de carga (plan Â§11.2).

Crea, de forma reproducible y ficticia:

- 10 000 productos con nombres, cÃ³digos y presentaciones variadas
- 500 proveedores
- 100 000 ventas histÃ³ricas con varias lÃ­neas
- 500 000 movimientos de inventario

Uso (solo sobre una base de DESARROLLO o de pruebas):
    python -m app.cli.datos_carga --productos 10000 --proveedores 500 \
        --ventas 100000 --avance 5000

AVISO: no lo ejecute contra la base de producciÃ³n.
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Abastecimiento,
    Almacen,
    Categoria,
    DetalleAbastecimiento,
    DetalleVenta,
    Dimension,
    Existencia,
    MovimientoInventario,
    PresentacionProducto,
    Producto,
    ProductoProveedor,
    Proveedor,
    UnidadMedida,
    Usuario,
    Venta,
)
from app.db.session import SessionLocal
from app.services import catalogo
from app.domain.unidades import q4


def _volcar(db: Session, modelo: type, filas: list[dict]) -> None:
    """Inserta un lote de filas de forma directa (mÃ¡s rÃ¡pido que el ORM)."""
    if filas:
        db.execute(insert(modelo), filas)

PALABRAS = [
    "Arroz", "Fideo", "AzÃºcar", "Aceite", "Leche", "Gaseosa", "Agua", "JabÃ³n",
    "Detergente", "Papel", "CafÃ©", "TÃ©", "Sal", "Pan", "Galleta", "Biscuit",
    "AtÃºn", "Leche evaporada", "Mermelada", "Chocolate", "Cereal", "Yogurt",
    "Mantequilla", "Queso", "JamÃ³n", "Hot dog", "Frijoles", "Lentejas",
    "Arvejas", "Mayonesa", "Ketchup", "Mostaza", "Vinagre", "Salsa",
    "Espagueti", "Harina", "Maicena", "Huevos", "Tomate", "Cebolla", "Papa",
]
PRESENTACIONES = {
    "UND": [("unidad", 1), ("paquete x6", 6), ("caja x24", 24)],
    "GR": [("1 kg", 1000), ("saco 50 kg", 50000)],
    "ML": [("botella 1 L", 1000), ("bidÃ³n 5 L", 5000)],
}
CATEGORIAS = [
    "Abarrotes", "Bebidas", "LÃ¡cteos", "PanaderÃ­a", "Aseo del hogar",
    "Cuidado personal", "Snacks", "Granos y menestras", "Conservas", "Condimentos",
]


def _preparar_consola() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass


_preparar_consola()


def _unidades(db: Session) -> dict[str, UnidadMedida]:
    resultado = {}
    for codigo, nombre, dimension in (
        ("UND", "Unidad", Dimension.UNIDAD),
        ("GR", "Gramo", Dimension.PESO),
        ("ML", "Mililitro", Dimension.VOLUMEN),
    ):
        unidad = db.execute(
            select(UnidadMedida).where(UnidadMedida.codigo == codigo)
        ).scalar_one_or_none()
        if unidad is None:
            unidad = UnidadMedida(
                codigo=codigo, nombre=nombre, dimension=dimension, paso_minimo=1
            )
            db.add(unidad)
            db.flush()
        resultado[codigo] = unidad
    return resultado


def generar(
    productos: int = 10_000,
    proveedores: int = 500,
    ventas: int = 100_000,
    lineas_por_venta: int = 3,
    semilla: int = 20261109,
) -> None:
    aleatorio = random.Random(semilla)
    db = SessionLocal()
    try:
        unidades = _unidades(db)
        almacen = db.execute(
            select(Almacen).where(Almacen.es_principal.is_(True))
        ).scalar_one_or_none()
        if almacen is None:
            almacen = Almacen(nombre="AlmacÃ©n principal", activo=True, es_principal=True)
            db.add(almacen)
            db.flush()
        usuario = db.execute(
            select(Usuario).where(Usuario.activo.is_(True)).order_by(Usuario.id)
        ).scalars().first()
        if usuario is None:
            print("Se requiere un usuario activo. Ejecute antes la instalaciÃ³n inicial.")
            return

        categorias = []
        for nombre in CATEGORIAS:
            categoria = db.execute(
                select(Categoria).where(Categoria.nombre == nombre)
            ).scalar_one_or_none()
            if categoria is None:
                categoria = Categoria(nombre=nombre)
                db.add(categoria)
                db.flush()
            categorias.append(categoria)

        # --- Proveedores ----------------------------------------------------
        print(f"Generando {proveedores} proveedores...")
        lista_proveedores: list[Proveedor] = []
        for indice in range(1, proveedores + 1):
            codigo = f"PRV-C{indice:05d}"
            existente = db.execute(
                select(Proveedor).where(Proveedor.codigo == codigo)
            ).scalar_one_or_none()
            if existente is None:
                existente = Proveedor(
                    codigo=codigo,
                    razon_social=f"Distribuidora Carga {indice} SAC",
                    nombre_comercial=f"Distribuidora {indice}",
                    activo=True,
                )
                db.add(existente)
                db.flush()
            lista_proveedores.append(existente)
        db.commit()

        # --- Productos ------------------------------------------------------
        print(f"Generando {productos} productos...")
        for indice in range(1, productos + 1):
            codigo = f"CAR-{indice:06d}"
            if db.execute(
                select(Producto.id).where(Producto.codigo == codigo)
            ).scalar_one_or_none():
                continue
            unidad_codigo = aleatorio.choice(["UND", "GR", "ML"])
            nombre = (
                f"{aleatorio.choice(PALABRAS)} {aleatorio.choice(PALABRAS)} "
                f"{aleatorio.choice(['250 g', '500 ml', '1 kg', 'x12', 'especial'])}"
            )
            producto = catalogo.crear_producto(
                db,
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "categoria_id": aleatorio.choice(categorias).id,
                    "unidad_base_id": unidades[unidad_codigo].id,
                    "stock_minimo_base": "0",
                    "permite_fraccion": unidad_codigo != "UND",
                    "activo": True,
                    "presentaciones": [
                        {
                            "nombre": nombre_presentacion,
                            "factor_base": str(factor),
                            "precio_venta": str(
                                Decimal(aleatorio.randrange(150, 9000)) / Decimal(100)
                            ),
                        }
                        for nombre_presentacion, factor in PRESENTACIONES[unidad_codigo]
                    ],
                },
            )
            proveedor = aleatorio.choice(lista_proveedores)
            presentacion = producto.presentaciones[0]
            vinculo = ProductoProveedor(
                producto_id=producto.id,
                proveedor_id=proveedor.id,
                habitual=True,
                presentacion_id=presentacion.id,
            )
            db.add(vinculo)
            if indice % 1000 == 0:
                db.commit()
                print(f"  Â· {indice} productos")
        db.commit()

        # --- Ventas histÃ³ricas ------------------------------------------------
        total_productos = db.execute(select(func.count()).select_from(Producto)).scalar_one()
        print(f"Generando {ventas} ventas sobre {total_productos} productos...")
        codigos = db.execute(select(Producto.codigo).order_by(Producto.codigo)).scalars().all()
        productos = db.execute(select(Producto).options(selectinload(Producto.presentaciones))).scalars().all()

        lote_ventas: list[dict] = []
        lote_detalles: list[dict] = []
        lote_movimientos: list[dict] = []
        saldo_por_producto: dict[int, Decimal] = {}
        inicio_id = db.execute(select(func.coalesce(func.max(Venta.id), 0))).scalar_one() + 1

        for numero_venta in range(1, ventas + 1):
            fecha = date.today() - timedelta(days=aleatorio.randrange(0, 365))
            venta_id = inicio_id + numero_venta - 1
            total = Decimal("0")
            costo = Decimal("0")
            lineas = []
            for _ in range(aleatorio.randrange(1, lineas_por_venta + 1)):
                producto = aleatorio.choice(productos)
                presentacion = aleatorio.choice(producto.presentaciones)
                cantidad = (
                    Decimal(aleatorio.randrange(1, 40)) / Decimal(10)
                    if presentacion.permite_fraccion or producto.permite_fraccion
                    else Decimal(aleatorio.randrange(1, 10))
                )
                factor = Decimal(presentacion.factor_base)
                precio = Decimal(presentacion.precio_venta)
                subtotal = q4(cantidad * precio)
                total += subtotal
                costo += q4(cantidad * factor * Decimal("2.10"))
                lineas.append(
                    {
                        "venta_id": venta_id,
                        "producto_id": producto.id,
                        "presentacion_id": presentacion.id,
                        "cantidad": q4(cantidad),
                        "factor_snapshot": factor,
                        "cantidad_base": q4(cantidad * factor),
                        "precio_unitario": precio,
                        "costo_base_snapshot": Decimal("2.10"),
                        "subtotal": subtotal,
                        "costo_total_linea": q4(cantidad * factor * Decimal("2.10")),
                    }
                )
                saldo = saldo_por_producto.get(producto.id, Decimal("0")) - q4(cantidad * factor)
                saldo_por_producto[producto.id] = saldo
                lote_movimientos.append(
                    {
                        "producto_id": producto.id,
                        "almacen_id": almacen.id,
                        "tipo": "VENTA",
                        "cantidad_base_signed": -q4(cantidad * factor),
                        "saldo_base_despues": saldo,
                        "costo_unitario_base": Decimal("2.10"),
                        "origen_tipo": "VENTA",
                        "origen_id": venta_id,
                        "referencia": f"CV-{numero_venta:07d}",
                        "usuario_id": usuario.id,
                    }
                )

            lote_ventas.append(
                {
                    "id": venta_id,
                    "numero": f"CV-{numero_venta:07d}",
                    "almacen_id": almacen.id,
                    "fecha": fecha,
                    "estado": "CONFIRMADO",
                    "usuario_id": usuario.id,
                    "total": q4(total),
                    "costo_total": q4(costo),
                }
            )
            lote_detalles.extend(lineas)

            if len(lote_ventas) >= 1000:
                _volcar(db, Venta, lote_ventas)
                _volcar(db, DetalleVenta, lote_detalles)
                _volcar(db, MovimientoInventario, lote_movimientos)
                lote_ventas, lote_detalles, lote_movimientos = [], [], []
                print(f"  Â· {numero_venta} ventas")

        if lote_ventas:
            _volcar(db, Venta, lote_ventas)
            _volcar(db, DetalleVenta, lote_detalles)
            _volcar(db, MovimientoInventario, lote_movimientos)
        db.commit()

        # Existencias coherentes con el kardex generado.
        print("Actualizando existencias...")
        db.execute(update(Existencia).values(cantidad_base=0, costo_promedio_base=Decimal("2.10")))
        for producto_id, saldo in saldo_por_producto.items():
            if saldo <= 0:
                db.execute(
                    update(Existencia)
                    .where(
                        Existencia.producto_id == producto_id,
                        Existencia.almacen_id == almacen.id,
                    )
                    .values(cantidad_base=saldo)
                )
        db.commit()

        movimientos = db.execute(
            select(func.count()).select_from(MovimientoInventario)
        ).scalar_one()
        print(
            f"Conjunto de datos listo: {total_productos} productos, "
            f"{len(lista_proveedores)} proveedores, {ventas} ventas, {movimientos} movimientos."
        )
        print("Datos FICTICIOS: solo para pruebas de rendimiento.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generador de datos de carga (ficticios)")
    parser.add_argument("--productos", type=int, default=10_000)
    parser.add_argument("--proveedores", type=int, default=500)
    parser.add_argument("--ventas", type=int, default=100_000)
    parser.add_argument("--semilla", type=int, default=20261109)
    args = parser.parse_args()
    generar(
        productos=args.productos,
        proveedores=args.proveedores,
        ventas=args.ventas,
        semilla=args.semilla,
    )


if __name__ == "__main__":
    main()

