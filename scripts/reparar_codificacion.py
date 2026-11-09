"""Repara la doble codificación UTF-8 (mojibake) en los archivos del proyecto.

Qué ocurre: algunos archivos se guardaron como UTF-8 misinterpreted y luego se
volvieron a codificar, de modo que una vocal acentuada quedo como dos
visible en los mensajes al usuario, en la plantilla de importación y en la
interfaz.

La reparación se hace línea a línea y solo se acepta si reduce los indicadores
de corrupción; nunca se toca una línea correcta. Al final se elimina la marca
BOM y el archivo se guarda en UTF-8 sin BOM.

Uso:
    python scripts/reparar_codificacion.py --simular          # solo informa
    python scripts/reparar_codificacion.py --aplicar          # repara
    python scripts/reparar_codificacion.py --aplicar --ruta backend/app
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Indicadores de doble codificación UTF-8 -> latin1 -> UTF-8.
INDICADORES = re.compile(r"[\u00c2\u00c3][\u0080-\u00bf]|[\u00e2]\u20ac|[\u00ef]\u00bb\u00bf|\ufffd")

EXTENSIONES = {".py", ".ts", ".tsx", ".md", ".css", ".js", ".json", ".ps1", ".sh", ".html"}
CARPETAS = ["backend/app", "backend/alembic", "frontend/src", "docs", "scripts", "."]


def contar(texto: str) -> int:
    return len(INDICADORES.findall(texto))


def reparar_linea(linea: str) -> str | None:
    """Devuelve la línea reparada, o None si no se puede mejorar."""
    if not INDICADORES.search(linea):
        return None
    try:
        candidata = linea.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    if contar(candidata) < contar(linea):
        return candidata
    return None


def reparar_texto(texto: str) -> tuple[str, int]:
    lineas = texto.splitlines()
    reparadas = 0
    salida = []
    for linea in lineas:
        nueva = reparar_linea(linea)
        if nueva is not None:
            reparadas += 1
            salida.append(nueva)
        else:
            salida.append(linea)
    return "\n".join(salida) + ("\n" if texto.endswith("\n") else ""), reparadas


def archivos(carpeta: str) -> list[Path]:
    base = RAIZ / carpeta
    if base.is_file():
        return [base]
    encontrados = []
    for ruta in base.rglob("*"):
        if not ruta.is_file() or ruta.suffix not in EXTENSIONES:
            continue
        if any(parte in ruta.parts for parte in ("node_modules", "dist", ".git", ".venv")):
            continue
        encontrados.append(ruta)
    return sorted(encontrados)


def main() -> None:
    parser = argparse.ArgumentParser(description="Repara la doble codificación UTF-8")
    parser.add_argument("--simular", action="store_true")
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--ruta", default="", help="Subcarpeta a revisar (por defecto, todo).")
    args = parser.parse_args()
    if not (args.simular or args.aplicar):
        parser.error("Indique --simular o --aplicar")

    carpetas = [args.ruta] if args.ruta else CARPETAS
    vistas = set()
    total_archivos = 0
    total_lineas = 0
    total_bom = 0

    for carpeta in carpetas:
        for ruta in archivos(carpeta):
            if ruta in vistas:
                continue
            vistas.add(ruta)
            crudo = ruta.read_bytes()
            tiene_bom = crudo.startswith(b"\xef\xbb\xbf")
            if tiene_bom:
                crudo = crudo[3:]
            try:
                texto = crudo.decode("utf-8")
            except UnicodeDecodeError:
                continue
            reparado, lineas = reparar_texto(texto)
            if lineas == 0 and not tiene_bom:
                continue
            if lineas:
                total_archivos += 1
                total_lineas += lineas
                print(f"{ruta.relative_to(RAIZ).as_posix()}: {lineas} lineas reparadas")
            elif tiene_bom:
                print(f"{ruta.relative_to(RAIZ).as_posix()}: se retiro la marca BOM")
            if tiene_bom:
                total_bom += 1
            if args.aplicar:
                ruta.write_bytes(reparado.encode("utf-8"))

    print()
    print(
        f"{'Reparados' if args.aplicar else 'A reparar'}: {total_archivos} archivos, "
        f"{total_lineas} lineas. Archivos con BOM: {total_bom}."
    )


if __name__ == "__main__":
    main()
