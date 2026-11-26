"""Limpieza de la base de datos (empezar de cero).

Hay dos niveles, según lo que se quiera dejar:

- **Limpiar la operación** (`limpiar_operacion`): vacía ventas, ingresos,
  ajustes, movimientos, existencias, lotes y auditoría, y **conserva todo el
  catálogo** (productos, presentaciones, proveedores, marcas y categorías).
  Es lo que se usa para «empezar de cero con el catálogo» sin perderlo.

- **Reiniciar la base** (`reiniciar_base`): deja la base **totalmente vacía**.
  Además de la operación, borra el catálogo entero. **Conserva** los usuarios,
  sus roles, el almacén, las unidades de medida y la configuración del
  negocio (nombre, RUC, reglas de la caja): sin ellos no se puede entrar al
  sistema ni imprimir un ticket.

Ambos comandos son reversibles solo con un respaldo: haga uno antes
(`scripts\\respaldo\\crear-respaldo.ps1`).

Uso:
    python -m app.cli.limpiar_operacion --simular
    python -m app.cli.limpiar_operacion
    python -m app.cli.reiniciar_base --simular
    python -m app.cli.reiniciar_base
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text


def _preparar_consola() -> None:
    """Evita errores de codificación en la consola de Windows (cp1252)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


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

#: Tablas del catálogo: solo se vacían al reiniciar la base entera.
TABLAS_CATALOGO = [
    "productos_proveedores",
    "presentaciones_producto",
    "productos",
    "proveedores",
    "marcas",
    "categorias",
]

#: Tablas que se conservan siempre: sin ellas no se puede entrar al sistema.
TABLAS_ESENCIALES = [
    "usuarios",
    "usuario_roles",
    "roles",
    "almacenes",
    "unidades_medida",
    "configuracion",
]


def contar(conexion, tabla: str) -> int:
    """Cuántas filas hay en una tabla."""
    return conexion.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar_one()


def _simular_operacion(conexion, tablas: list[str], titulo: str) -> None:
    print(titulo)
    for tabla in tablas:
        print(f"   {tabla:28} {contar(conexion, tabla):>5} filas")


def _simular(conexion, *, con_catalogo: bool) -> None:
    """Muestra qué se borraría, sin tocar nada."""
    print("SIMULACIÓN (no se borra nada)")
    print()
    _simular_operacion(conexion, TABLAS_OPERACION, "Operación que se vacía:")
    if con_catalogo:
        print()
        _simular_operacion(conexion, TABLAS_CATALOGO, "Catálogo que se vacía:")
    print()
    print("Se conservan (sin esto el sistema no arranca):")
    for tabla in TABLAS_ESENCIALES:
        print(f"   {tabla:28} {contar(conexion, tabla):>5} filas")


def _vaciar_operacion(conexion) -> None:
    """Vacía las tablas de la operación."""
    for tabla in TABLAS_OPERACION:
        conexion.execute(text(f'TRUNCATE TABLE "{tabla}" RESTART IDENTITY CASCADE'))


def _vaciar_catalogo(conexion) -> None:
    """Vacía el catálogo: productos, presentaciones, proveedores, marcas y categorías."""
    for tabla in TABLAS_CATALOGO:
        conexion.execute(text(f'DELETE FROM "{tabla}"'))


def _reiniciar_secuencias(conexion) -> None:
    """Las secuencias vuelven a cero: la primera venta será la V-000001."""
    conexion.execute(text("DELETE FROM secuencias"))


def limpiar(conexion=None, *, con_catalogo: bool = False) -> None:
    """Vacía la operación y conserva el catálogo.

    Si se pasa una conexión, se trabaja sobre ella (así las pruebas pueden
    usar su propia base). Si no, se abre una con el motor de la aplicación.
    """
    if conexion is None:
        from app.db.session import engine

        with engine.begin() as propia:
            _limpiar_en(propia, con_catalogo=con_catalogo)
        return

    _limpiar_en(conexion, con_catalogo=con_catalogo)


def _limpiar_en(conexion, *, con_catalogo: bool = False) -> None:
    # No se confirma aquí: la limpieza trabaja dentro de la transacción que
    # abrió el llamante (las pruebas usan su propia conexión).
    _vaciar_operacion(conexion)
    if con_catalogo:
        _vaciar_catalogo(conexion)
    _reiniciar_secuencias(conexion)


def reiniciar(conexion=None) -> None:
    """Deja la base totalmente vacía (sin operación ni catálogo)."""
    if conexion is None:
        from app.db.session import engine

        with engine.begin() as propia:
            _reiniciar_en(propia)
        return

    _reiniciar_en(conexion)


def _reiniciar_en(conexion) -> None:
    # Igual que en la limpieza: no confirma, trabaja en la transacción abierta.
    _vaciar_operacion(conexion)
    _vaciar_catalogo(conexion)
    _reiniciar_secuencias(conexion)


def _resumen(conexion) -> None:
    print("Base:")
    for tabla in (
        "productos",
        "presentaciones_producto",
        "proveedores",
        "marcas",
        "categorias",
        "lotes_inventario",
        "existencias",
        "movimientos_inventario",
        "ventas",
        "abastecimientos",
        "auditoria",
    ):
        print(f"   {tabla:28} {contar(conexion, tabla):>5} filas")
    print("Se conservan:")
    for tabla in TABLAS_ESENCIALES:
        print(f"   {tabla:28} {contar(conexion, tabla):>5} filas")


def main() -> int:
    _preparar_consola()

    analizador = argparse.ArgumentParser(
        description="Vacía la operación de la base y conserva el catálogo."
    )
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Muestra qué se borraría sin tocar nada.",
    )
    analizador.add_argument(
        "--incluir-catalogo",
        action="store_true",
        help="Borra también el catálogo (productos, proveedores, marcas y categorías).",
    )
    argumentos = analizador.parse_args()

    from app.db.session import engine

    with engine.connect() as conexion:
        if argumentos.simular:
            _simular(conexion, con_catalogo=argumentos.incluir_catalogo)
            return 0

    limpiar(con_catalogo=argumentos.incluir_catalogo)

    with engine.connect() as conexion:
        _resumen(conexion)
    return 0


__all__ = [
    "TABLAS_CATALOGO",
    "TABLAS_ESENCIALES",
    "TABLAS_OPERACION",
    "contar",
    "limpiar",
    "main",
    "reiniciar",
]


if __name__ == "__main__":
    sys.exit(main())
