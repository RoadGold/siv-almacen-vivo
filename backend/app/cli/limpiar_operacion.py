"""Deja la base limpia para empezar de cero, conservando el catálogo.

Borra **toda la operación** (ventas, ingresos, movimientos, ajustes, lotes,
impresiones y auditoría) y todo lo que no sea del catálogo de balanceados
(productos, proveedores, categorías y marcas de ejemplo). El stock queda en
cero: el negocio entra con el catálogo y las listas de precios, y las compras
reales se registran desde el sistema.

Se conserva:
- Los usuarios, sus roles y el almacén principal (para poder entrar).
- Las unidades de medida.
- El catálogo de balanceados (VITAMAXPRO/INVITA y TOMASINO) con sus precios.

Uso:
    python -m app.cli.limpiar_operacion            # limpia
    python -m app.cli.limpiar_operacion --simular  # muestra qué haría

AVISO: hace cambios irreversibles. Haga un respaldo antes.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from app.db.base import Base
from app.db import models  # noqa: F401  (registra los modelos)
from app.db.session import engine

#: Tablas con los datos de la operación: se vacían enteras.
TABLAS_OPERACION = [
    "impresiones_venta",
    "detalle_ventas",
    "ventas",
    "detalle_abastecimientos",
    "abastecimientos",
    "ajustes_inventario",
    "movimientos_inventario",
    "existencias",
    "lotes_precios",
    "lotes_inventario",
    "auditoria",
]

#: Marcas del catálogo de balanceados que se conservan.
MARCAS_CATALOGO = ("Vitamaxpro", "Invita", "Tomasino")


def _preparar_consola() -> None:
    """Evita errores de codificación en la consola de Windows (cp1252)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


def _contar(conexion, tabla: str, condicion: str = "") -> int:
    """Cuántas filas hay en una tabla (con una condición opcional)."""
    where = f" WHERE {condicion}" if condicion else ""
    return conexion.execute(text(f'SELECT COUNT(*) FROM "{tabla}"{where}')).scalar_one()


def _simular(conexion) -> None:
    """Muestra qué se borraría, sin tocar nada."""
    print("SIMULACIÓN (no se borra nada)")
    print()
    print("Operación que se vacía:")
    for tabla in TABLAS_OPERACION:
        print(f"   {tabla:28} { _contar(conexion, tabla):>5} filas")

    marcas = ", ".join(f"'{m}'" for m in MARCAS_CATALOGO)
    fuera = _contar(
        conexion,
        "productos",
        f"NOT EXISTS (SELECT 1 FROM marcas m WHERE m.id = productos.marca_id "
        f"AND m.nombre IN ({marcas}))",
    )
    proveedores_fuera = _contar(
        conexion,
        "proveedores",
        "razon_social NOT IN ('Vitamaxpro', 'Tomasino')",
    )
    print()
    print("Catálogo que NO es de balanceados (se borra):")
    print(f"   {'productos':28} {fuera:>5} filas")
    print(f"   {'proveedores':28} {proveedores_fuera:>5} filas")


def limpiar(conexion=None) -> None:
    """Vacía la operación y quita lo que no es del catálogo.

    Si se pasa una conexión, se trabaja sobre ella (así las pruebas pueden
    usar su propia base). Si no, se abre una con el motor de la aplicación.
    """
    if conexion is None:
        with engine.begin() as propia:
            _limpiar_en(propia)
        return

    _limpiar_en(conexion)


def _limpiar_en(conexion) -> None:
    """La limpieza, sobre una conexión ya abierta."""
    marcas = ", ".join(f"'{m}'" for m in MARCAS_CATALOGO)

    # --- 1. La operación, entera ----------------------------------------
    for tabla in TABLAS_OPERACION:
        conexion.execute(text(f'TRUNCATE TABLE "{tabla}" RESTART IDENTITY CASCADE'))

    # --- 2. Los vínculos con proveedores --------------------------------
    conexion.execute(text("DELETE FROM productos_proveedores"))

    # --- 3. Las presentaciones y los productos de ejemplo --------------
    # Se borra todo lo que no sea del catálogo, incluidos los productos
    # sin marca (marca_id nulo), que se crean al vuelo en algunos flujos.
    conexion.execute(
        text(
            """
            DELETE FROM presentaciones_producto
            WHERE producto_id IN (
                SELECT p.id FROM productos p
                LEFT JOIN marcas m ON m.id = p.marca_id
                WHERE m.nombre IS NULL OR m.nombre NOT IN ("""
            + marcas
            + """
            ))
            """
        )
    )
    conexion.execute(
        text(
            """
            DELETE FROM productos
            WHERE id IN (
                SELECT p.id FROM productos p
                LEFT JOIN marcas m ON m.id = p.marca_id
                WHERE m.nombre IS NULL OR m.nombre NOT IN ("""
            + marcas
            + """
            ))
            """
        )
    )

    # --- 4. Los proveedores de ejemplo ---------------------------------
    conexion.execute(
        text(
            "DELETE FROM proveedores "
            "WHERE razon_social IS NULL "
            "OR razon_social NOT IN ('Vitamaxpro', 'Tomasino')"
        )
    )

    # --- 5. Las categorías y marcas que quedaron vacías ----------------
    conexion.execute(
        text("DELETE FROM categorias WHERE id NOT IN (SELECT DISTINCT categoria_id FROM productos WHERE categoria_id IS NOT NULL)")
    )
    conexion.execute(
        text("DELETE FROM marcas WHERE id NOT IN (SELECT DISTINCT marca_id FROM productos WHERE marca_id IS NOT NULL)")
    )

    # --- 6. La configuración, a los valores de fábrica ------------------
    conexion.execute(text("DELETE FROM configuracion"))

    # --- 7. Las secuencias, para empezar de cero -----------------------
    conexion.execute(text("DELETE FROM secuencias"))

    # --- 8. Los identificadores, desde el uno --------------------------
    # Se reinician los de las tablas que se vaciaron, para que la primera
    # venta sea la V-000001 y el primer ingreso el A-000001.
    for tabla in (
        "productos",
        "presentaciones_producto",
        "proveedores",
        "ventas",
        "abastecimientos",
        "ajustes_inventario",
        "lotes_inventario",
    ):
        conexion.execute(
                text(
                    "SELECT setval("
                    "pg_get_serial_sequence(:tabla, 'id'), "
                    "COALESCE((SELECT MAX(id) FROM " + tabla + "), 0) + 1, false)"
                ),
                {"tabla": tabla},
            )


def main() -> int:
    _preparar_consola()

    analizador = argparse.ArgumentParser(
        description="Limpia la base y conserva el catálogo de balanceados."
    )
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Muestra qué se borraría sin tocar nada.",
    )
    argumentos = analizador.parse_args()

    with engine.connect() as conexion:
        if argumentos.simular:
            _simular(conexion)
            return 0

    limpiar()

    with engine.connect() as conexion:
        print("Base limpia:")
        print(f"   Productos del catálogo: {_contar(conexion, 'productos')}")
        print(f"   Presentaciones: {_contar(conexion, 'presentaciones_producto')}")
        print(f"   Proveedores: {_contar(conexion, 'proveedores')}")
        print(f"   Categorías: {_contar(conexion, 'categorias')}")
        print(f"   Marcas: {_contar(conexion, 'marcas')}")
        print(f"   Ventas: {_contar(conexion, 'ventas')}")
        print(f"   Ingresos: {_contar(conexion, 'abastecimientos')}")
        print(f"   Movimientos: {_contar(conexion, 'movimientos_inventario')}")
        print(f"   Existencias: {_contar(conexion, 'existencias')}")
        print(f"   Lotes: {_contar(conexion, 'lotes_inventario')}")
        print(f"   Auditoría: {_contar(conexion, 'auditoria')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
