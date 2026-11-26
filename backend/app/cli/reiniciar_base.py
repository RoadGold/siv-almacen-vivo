"""Deja la base de datos **totalmente vacía**, lista para presentar.

Se borra toda la operación (ventas, ingresos, ajustes, movimientos, existencias,
lotes, impresiones y auditoría) y todo el catálogo (productos, presentaciones,
proveedores, marcas y categorías).

**Se conservan** los usuarios y sus roles, el almacén, las unidades de medida y
la configuración del negocio: sin ellos no se puede entrar al sistema ni
imprimir un ticket.

Las secuencias se reinician, así que la primera venta será la `V-000001` y el
primer ingreso el `A-000001`.

AVISO: es irreversible. Haga un respaldo antes
(`scripts\\respaldo\\crear-respaldo.ps1`).

Uso:
    python -m app.cli.reiniciar_base --simular
    python -m app.cli.reiniciar_base
"""

from __future__ import annotations

import argparse
import sys

from app.cli.limpiar_operacion import (
    TABLAS_CATALOGO,
    TABLAS_ESENCIALES,
    TABLAS_OPERACION,
    _preparar_consola,
    _resumen,
    _simular,
    reiniciar,
)


def main() -> int:
    _preparar_consola()

    analizador = argparse.ArgumentParser(
        description="Deja la base de datos vacía (sin operación ni catálogo)."
    )
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Muestra qué se borraría sin tocar nada.",
    )
    argumentos = analizador.parse_args()

    from app.db.session import engine

    with engine.connect() as conexion:
        if argumentos.simular:
            _simular(conexion, con_catalogo=True)
            return 0

    print("AVISO: se borra todo el contenido de la base de datos.")
    reiniciar()

    with engine.connect() as conexion:
        _resumen(conexion)
    print()
    print("Base vacía. Para volver a llenarla:")
    print("   python -m app.cli.datos_balanceados_cargar")
    print("   python -m app.cli.cargar_inventario_tienda")
    return 0


__all__ = ["main"]


if __name__ == "__main__":
    sys.exit(main())
