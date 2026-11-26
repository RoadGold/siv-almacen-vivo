"""Genera el documento del esquema de la base de datos desde la base viva.

El documento describe **lo que hay realmente** en la base: tablas, columnas,
tipos, nulos, claves, foráneas e índices. Como se genera desde la propia base,
nunca se queda viejo: si cambia el esquema (una migración), se regenera.

Uso:
    python -m app.cli.esquema_base_datos            # escribe el documento
    python -m app.cli.esquema_base_datos --ver      # solo muestra el resumen
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DOCUMENTO = RAIZ / "docs" / "arquitectura" / "esquema-base-datos.md"


def _preparar_consola() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


_preparar_consola()

from sqlalchemy import text

from app.db.session import engine

#: Tablas del modelo, en el orden en que se presentan en el documento.
GRUPOS: list[tuple[str, list[str]]] = [
    (
        "Seguridad, roles y configuración",
        ["usuarios", "usuario_roles", "roles", "configuracion", "secuencias"],
    ),
    (
        "Almacén y catálogo",
        [
            "almacenes",
            "unidades_medida",
            "categorias",
            "marcas",
            "productos",
            "presentaciones_producto",
            "proveedores",
            "productos_proveedores",
        ],
    ),
    (
        "Inventario por lotes",
        [
            "lotes_inventario",
            "lotes_precios",
            "existencias",
            "movimientos_inventario",
            "ajustes_inventario",
        ],
    ),
    (
        "Operaciones comerciales",
        [
            "abastecimientos",
            "detalle_abastecimientos",
            "ventas",
            "detalle_ventas",
            "impresiones_venta",
        ],
    ),
    ("Auditoría", ["auditoria"]),
]

#: Qué significa cada cosa, para quien lea el documento sin conocer el sistema.
COMENTARIOS: dict[str, str] = {
    "usuarios": "Cuentas de acceso al sistema. La contraseña nunca se guarda en claro: se guarda su hash (Argon2id).",
    "usuario_roles": "Qué roles tiene cada usuario (un usuario puede tener varios).",
    "roles": "Los roles del sistema: `administrador` y `vendedor`. Los permisos se declaran aquí (AD-10).",
    "configuracion": "Clave/valor con los datos del negocio (nombre, RUC) y las reglas de la caja (descuento máximo, formato del ticket).",
    "secuencias": "Correlativos de comprobantes por almacén: `V-000001`, `A-000001`, `AJ-000001`.",
    "almacenes": "Almacenes del negocio. El primero activo es el principal.",
    "unidades_medida": "Unidades base: `UND` (unidad), `GR` (gramo), `ML` (mililitro). El paso mínimo define la fracción mínima.",
    "categorias": "Categorías de los productos (balanceados, mascotas, primario, medicamentos…).",
    "marcas": "Marcas de los productos (Vitamaxpro, Invita, Tomasino, Sequeiros…).",
    "productos": "Maestro de productos. `nombre_normalizado` es el nombre sin acentos ni mayúsculas, para las búsquedas tolerantes.",
    "presentaciones_producto": "Los empaques de cada producto (saco 40 kg, caja x24, bolsa 1 kg). `factor_base` convierte a la unidad base.",
    "proveedores": "Los proveedores (distribuidores).",
    "productos_proveedores": "Vínculo N:M entre productos y proveedores, con su presentación habitual y el último costo.",
    "lotes_inventario": "Cada línea de ingreso crea un lote: su stock, su costo y su precio de venta propios. Es la fuente de verdad del inventario.",
    "lotes_precios": "Precio de venta de una presentación dentro de un lote (un mismo lote se puede vender en sacos o por kilos).",
    "existencias": "Stock consolidado por (almacén, producto). Es la lectura rápida; su valor se recalcula desde los lotes.",
    "movimientos_inventario": "El kardex: cada entrada, salida, reverso y ajuste con su saldo. Nunca se borra.",
    "ajustes_inventario": "Ajustes administrativos (pérdida, rotura, conteo) con su motivo.",
    "abastecimientos": "Cabecera de los ingresos de mercadería. Siempre tienen proveedor.",
    "detalle_abastecimientos": "Líneas del ingreso, con el *snapshot* del factor y el costo, y el lote que generaron.",
    "ventas": "Cabecera de las ventas: total, costo, forma de pago, vuelto y deuda.",
    "detalle_ventas": "Líneas de la venta, con el *snapshot* del precio y del costo, y el lote del que salió la mercadería.",
    "impresiones_venta": "Cada impresión del ticket, con su resultado (para reimprimir y auditar).",
    "auditoria": "Bitácora de las acciones sensibles (cambios de precio, anulaciones, ajustes).",
}

REGLAS = """\
- **Todo el dinero y las cantidades son `NUMERIC`**, nunca `float`: los importes
  viajan como cadenas decimales y la aritmética es exacta (AD-02).
- **Nada se borra**: los productos, proveedores y categorías se desactivan
  (`activo = false`); las operaciones se anulan o se revierten con contramovimientos.
- **Los detalles guardan *snapshots*** (factor, precio y costo del momento): cambiar
  un precio o un factor hoy no altera las ventas de ayer (AD-09).
- **El lote es la fuente de verdad del inventario**: `existencias` es la caché
  consolidada, y `movimientos_inventario` es el historial (AD-15).
- **Las claves foráneas que borran** lo hacen con `SET NULL` o `CASCADE` para no
  perder la evidencia comercial (plan §6.5).
- **Los importes se redondean en el servidor**: 2 decimales para dinero, 4 para
  cantidades y 6 para costos unitarios.
"""


def _columnas(db) -> dict[str, list[dict]]:
    """Columnas de cada tabla, con su tipo, nulabilidad y valor por defecto."""
    filas = db.execute(
        text(
            """
            SELECT table_name, column_name, data_type, character_maximum_length,
                   numeric_precision, numeric_scale, is_nullable, column_default
              FROM information_schema.columns
             WHERE table_schema = 'public'
             ORDER BY table_name, ordinal_position
            """
        )
    ).all()
    tablas: dict[str, list[dict]] = {}
    for (
        tabla,
        columna,
        tipo,
        largo,
        precision,
        escala,
        nullable,
        defecto,
    ) in filas:
        tipo_texto = tipo
        if tipo == "character varying" and largo:
            tipo_texto = f"varchar({largo})"
        elif tipo == "numeric" and precision:
            tipo_texto = f"numeric({precision},{escala})"
        elif tipo == "timestamp with time zone":
            tipo_texto = "timestamptz"
        tablas.setdefault(tabla, []).append(
            {
                "columna": columna,
                "tipo": tipo_texto,
                "nulo": nullable == "YES",
                "defecto": (defecto or "").strip(),
            }
        )
    return tablas


def _claves(db) -> dict[str, dict]:
    """Clave primaria, foráneas y únicas de cada tabla."""
    tablas: dict[str, dict] = {}

    for tabla, columna in db.execute(
        text(
            """
            SELECT tc.table_name, kcu.column_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu
                ON kcu.constraint_name = tc.constraint_name
             WHERE tc.constraint_type = 'PRIMARY KEY'
               AND tc.table_schema = 'public'
            """
        )
    ).all():
        tablas.setdefault(tabla, {"pk": [], "fk": [], "unicas": []})["pk"].append(columna)

    for tabla, columna, destino, destino_columna, regla in db.execute(
        text(
            """
            SELECT tc.table_name, kcu.column_name,
                   ccu.table_name AS destino,
                   ccu.column_name AS destino_columna,
                   rc.delete_rule
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu
                ON kcu.constraint_name = tc.constraint_name
              JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
              JOIN information_schema.referential_constraints rc
                ON rc.constraint_name = tc.constraint_name
             WHERE tc.constraint_type = 'FOREIGN KEY'
               AND tc.table_schema = 'public'
            """
        )
    ).all():
        tablas.setdefault(tabla, {"pk": [], "fk": [], "unicas": []})["fk"].append(
            {"columna": columna, "destino": destino, "destino_columna": destino_columna, "regla": regla}
        )

    for tabla, columna in db.execute(
        text(
            """
            SELECT tc.table_name, kcu.column_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu
                ON kcu.constraint_name = tc.constraint_name
             WHERE tc.constraint_type = 'UNIQUE'
               AND tc.table_schema = 'public'
            """
        )
    ).all():
        tablas.setdefault(tabla, {"pk": [], "fk": [], "unicas": []})["unicas"].append(columna)

    return tablas


def _indices(db) -> dict[str, list[str]]:
    """Índices de cada tabla."""
    indices: dict[str, list[str]] = {}
    for tabla, nombre in db.execute(
        text(
            """
            SELECT tablename, indexname
              FROM pg_indexes
             WHERE schemaname = 'public'
             ORDER BY tablename, indexname
            """
        )
    ).all():
        indices.setdefault(tabla, []).append(nombre)
    return indices


def _conteos(db) -> dict[str, int]:
    """Filas de cada tabla del modelo."""
    conteos: dict[str, int] = {}
    for tabla in [t for _, grupo in GRUPOS for t in grupo]:
        conteos[tabla] = db.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar_one()
    return conteos


def _diagrama(claves: dict[str, dict]) -> str:
    """Diagrama ER en mermaid, a partir de las claves foráneas."""
    orden = [t for _, grupo in GRUPOS for t in grupo]
    lineas = ["erDiagram"]
    declaradas: set[str] = set()
    for tabla in orden:
        datos = claves.get(tabla)
        if not datos or not datos["pk"]:
            continue
        declaradas.add(tabla)
        for columna in datos["pk"]:
            lineas.append(f"    {tabla} {{{columna} PK}}")
    for tabla in orden:
        datos = claves.get(tabla)
        if not datos:
            continue
        for fk in datos["fk"]:
            destino = fk["destino"]
            etiqueta = fk["columna"].upper()
            lineas.append(f"    {tabla} ||--o{{ {destino} : \"{etiqueta}\"")
    return "\n".join(lineas)


def _seccion_tabla(
    tabla: str,
    columnas: list[dict],
    datos: dict,
    indices: list[str],
    conteo: int,
) -> list[str]:
    lineas: list[str] = []
    lineas.append(f"### `{tabla}`")
    lineas.append("")
    if COMENTARIOS.get(tabla):
        lineas.append(COMENTARIOS[tabla])
        lineas.append("")

    claves = set(datos["pk"]) | set(datos["unicas"])
    lineas.append("| Columna | Tipo | Nulo | Clave | Valor por defecto |")
    lineas.append("|---|---|:---:|---|---|")
    for col in columnas:
        marca = ""
        if col["columna"] in datos["pk"]:
            marca = "PK"
        elif col["columna"] in datos["unicas"]:
            marca = "única"
        else:
            for fk in datos["fk"]:
                if fk["columna"] == col["columna"]:
                    marca = f"FK → `{fk['destino']}.{fk['destino_columna']}` ({fk['regla'].lower()})"
        lineas.append(
            f"| `{col['columna']}` | {col['tipo']} | "
            f"{'sí' if col['nulo'] else 'no'} | {marca} | "
            f"{('`' + col['defecto'] + '`') if col['defecto'] else '—'} |"
        )
    lineas.append("")
    lineas.append(f"Filas ahora mismo: **{conteo}**.")
    if indices:
        lineas.append("")
        lineas.append("Índices: " + ", ".join(f"`{i}`" for i in indices) + ".")
    lineas.append("")
    return lineas


def generar_texto() -> str:
    """Construye el documento del esquema a partir de la base viva."""
    with engine.connect() as db:
        columnas = _columnas(db)
        claves = _claves(db)
        indices = _indices(db)
        conteos = _conteos(db)
        try:
            version = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        except Exception:  # pragma: no cover
            version = "desconocida"

    lineas: list[str] = []
    lineas.append("# Esquema de la base de datos · SIV · Almacén Vivo")
    lineas.append("")
    lineas.append(
        "> Documento generado automáticamente desde la base de datos viva con "
        "`python -m app.cli.esquema_base_datos`. Si cambia el esquema, "
        "vuelve a generarlo: así nunca queda viejo."
    )
    lineas.append("")
    lineas.append(f"Versión del esquema (Alembic): `{version}`.")
    lineas.append("")

    lineas.append("## 1. Reglas del modelo")
    lineas.append("")
    lineas.append(REGLAS)

    lineas.append("## 2. Diagrama de relaciones")
    lineas.append("")
    lineas.append("```mermaid")
    lineas.append(_diagrama(claves))
    lineas.append("```")
    lineas.append("")

    lineas.append("## 3. Tablas")
    lineas.append("")
    for titulo, grupo in GRUPOS:
        lineas.append(f"### {titulo}")
        lineas.append("")
        for tabla in grupo:
            if tabla not in columnas:
                continue
            lineas.extend(
                _seccion_tabla(
                    tabla,
                    columnas[tabla],
                    claves.get(tabla, {"pk": [], "fk": [], "unicas": []}),
                    indices.get(tabla, []),
                    conteos.get(tabla, 0),
                )
            )

    lineas.append("## 4. Base limpia: lista de comprobación")
    lineas.append("")
    lineas.append("Una base **limpia** (la de una instalación recién hecha) tiene:")
    lineas.append("")
    lineas.append("| Tabla | Estado esperado |")
    lineas.append("|---|---|")
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
        "ajustes_inventario",
        "impresiones_venta",
        "auditoria",
    ):
        lineas.append(f"| `{tabla}` | 0 filas |")
    for tabla in ("usuarios", "almacenes", "unidades_medida"):
        lineas.append(f"| `{tabla}` | las que tenga (no se borran) |")
    lineas.append("")
    lineas.append("Y las secuencias en cero, para que la primera venta sea `V-000001`.")
    lineas.append("")
    lineas.append("Comprobaciones:")
    lineas.append("")
    lineas.append("```powershell")
    lineas.append("# Ver el estado desde el sistema")
    lineas.append("#   Administrar -> Diagnóstico -> «Estado de la base de datos»")
    lineas.append("")
    lineas.append("# Ver el estado desde la consola")
    lineas.append("cd backend")
    lineas.append(".\\.venv\\Scripts\\python.exe -m app.cli.reiniciar_base --simular")
    lineas.append("```")
    lineas.append("")

    lineas.append("## 5. Cómo dejar la base en este estado")
    lineas.append("")
    lineas.append("```powershell")
    lineas.append("cd backend")
    lineas.append("")
    lineas.append("# Vaciar la operación y conservar el catálogo")
    lineas.append(".\\.venv\\Scripts\\python.exe -m app.cli.limpiar_operacion --simular")
    lineas.append(".\\.venv\\Scripts\\python.exe -m app.cli.limpiar_operacion")
    lineas.append("")
    lineas.append("# Dejar la base totalmente vacía (sin catálogo ni stock)")
    lineas.append(".\\.venv\\Scripts\\python.exe -m app.cli.reiniciar_base --simular")
    lineas.append(".\\.venv\\Scripts\\python.exe -m app.cli.reiniciar_base")
    lineas.append("")
    lineas.append("# Volver a llenarla")
    lineas.append(".\\.venv\\Scripts\\python.exe -m app.cli.datos_balanceados_cargar")
    lineas.append(".\\.venv\\Scripts\\python.exe -m app.cli.cargar_inventario_tienda")
    lineas.append("```")
    lineas.append("")

    return "\n".join(lineas) + "\n"


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Genera el documento del esquema de la base de datos."
    )
    analizador.add_argument(
        "--ver",
        action="store_true",
        help="Solo muestra un resumen; no escribe el documento.",
    )
    args = analizador.parse_args()

    if args.ver:
        with engine.connect() as db:
            conteos = _conteos(db)
        print("Resumen de la base:")
        for tabla, conteo in conteos.items():
            print(f"   {tabla:28} {conteo:>6} filas")
        return 0

    texto = generar_texto()
    DOCUMENTO.parent.mkdir(parents=True, exist_ok=True)
    DOCUMENTO.write_text(texto, encoding="utf-8")
    print(f"Esquema escrito en {DOCUMENTO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
