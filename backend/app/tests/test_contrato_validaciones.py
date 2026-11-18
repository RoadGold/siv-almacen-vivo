"""El contrato de validaciones está al día.

Las reglas viven en los schemas del backend. El cliente las recibe en
`frontend/src/shared/contrato/reglas.json`, que se genera con:

    python -m app.core.contrato_cli --escribir

Este test falla si alguien cambia una regla en el backend y no regenera el
archivo: así el cliente no se queda con reglas viejas.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.contrato import CONTRATO, contrato_completo
from app.core.contrato_cli import RUTA_CLIENTE


def _contenido_actual() -> dict:
    if not RUTA_CLIENTE.exists():
        raise AssertionError(
            f"No existe el archivo del cliente: {RUTA_CLIENTE}. "
            "Genérelo con: python -m app.core.contrato_cli --escribir"
        )
    return json.loads(RUTA_CLIENTE.read_text(encoding="utf-8"))


def test_el_archivo_del_cliente_existe() -> None:
    assert RUTA_CLIENTE.exists(), (
        f"Falta {RUTA_CLIENTE}. Genérelo con: python -m app.core.contrato_cli --escribir"
    )


def test_el_contrato_del_cliente_esta_al_dia() -> None:
    """El archivo del cliente tiene las mismas reglas que los schemas."""
    actual = _contenido_actual()
    esperado = contrato_completo()
    if actual != esperado:
        diferencias = [
            grupo
            for grupo in esperado["reglas"]
            if actual.get("reglas", {}).get(grupo) != esperado["reglas"][grupo]
        ]
        raise AssertionError(
            "El contrato del cliente está desactualizado. "
            "Regenerarlo con: python -m app.core.contrato_cli --escribir. "
            f"Grupos distintos: {diferencias or 'cambios en las formas de pago'}"
        )


def test_cada_grupo_tiene_reglas() -> None:
    """Ningún grupo del contrato está vacío: si no, el cliente no refleja nada."""
    vacios = [grupo for grupo, reglas in CONTRATO.items() if not reglas]
    assert not vacios, f"Grupos sin reglas: {vacios}"


def test_las_formas_de_pago_estan_listas() -> None:
    """La caja ofrece las formas de pago que el backend acepta."""
    from app.domain.pagos import FORMAS_PAGO

    assert set(_contenido_actual()["formas_pago"]) == set(FORMAS_PAGO)
