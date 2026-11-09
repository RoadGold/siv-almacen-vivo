"""Vigila la codificación de los archivos del proyecto.

Algunos archivos se guardaron antes como UTF-8 interpretado como latin-1 y
quedaron con doble codificación («código» como «cÃ³digo»). El síntoma es texto
roto en los mensajes al usuario, en la plantilla de importación y en la interfaz.

Esta prueba recorre el proyecto y falla si aparece cualquier resto, para que el
problema no vuelva a colarse.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]

# Indicadores de doble codificación UTF-8 -> latin1 -> UTF-8.
INDICADORES = re.compile(r"[\u00c2\u00c3][\u0080-\u00bf]|[\u00e2]\u20ac|[\u00ef]\u00bb\u00bf|\ufffd")

CARPETAS = ["backend/app", "backend/alembic", "frontend/src", "docs", "scripts"]
EXTENSIONES = {".py", ".ts", ".tsx", ".md", ".css", ".js", ".json", ".ps1", ".sh", ".html"}


def _archivos() -> list[Path]:
    encontrados: list[Path] = []
    for carpeta in CARPETAS:
        base = RAIZ / carpeta
        if not base.exists():
            continue
        for ruta in base.rglob("*"):
            if not ruta.is_file() or ruta.suffix not in EXTENSIONES:
                continue
            if any(parte in ruta.parts for parte in ("node_modules", "dist", ".venv", ".git")):
                continue
            if ruta.name == Path(__file__).name:
                continue
            encontrados.append(ruta)
    return sorted(encontrados)


@pytest.mark.parametrize("ruta", _archivos(), ids=lambda p: p.as_posix())
def test_archivo_sin_doble_codificacion(ruta: Path) -> None:
    texto = ruta.read_bytes().decode("utf-8")
    coincidencias = INDICADORES.findall(texto)
    assert not coincidencias, (
        f"{ruta.relative_to(RAIZ).as_posix()} tiene {len(coincidencias)}(lineas) con doble "
        f"codificación. Ejecute: python scripts/reparar_codificacion.py --aplicar"
    )


def test_archivos_sin_bom() -> None:
    """Python y Node leen el BOM, pero rompe algunas herramientas: no debe haberlo."""
    con_bom = [
        ruta.relative_to(RAIZ).as_posix()
        for ruta in _archivos()
        if ruta.read_bytes().startswith(b"\xef\xbb\xbf")
    ]
    assert not con_bom, f"Archivos con BOM: {con_bom}"


def test_plantilla_de_importacion_reconocible() -> None:
    """Los encabezados de la plantilla deben ser los que el importador entiende."""
    import io

    from openpyxl import load_workbook

    from app.services import importador

    libro = load_workbook(io.BytesIO(importador.plantilla_excel()))
    encabezados = [str(celda.value) for celda in libro.active[1]]
    sin_reconocer = [
        encabezado for encabezado in encabezados if not importador._resolver_columna(encabezado)
    ]
    assert not sin_reconocer, f"Encabezados no reconocidos por el importador: {sin_reconocer}"
