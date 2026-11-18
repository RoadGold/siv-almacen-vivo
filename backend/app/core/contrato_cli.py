"""Publica el contrato de validaciones y lo deja en un archivo para el cliente.

Uso:
    python -m app.core.contrato            # muestra el contrato
    python -m app.core.contrato --escribir # lo guarda en frontend/src/shared/contrato/reglas.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.core.contrato import contrato_completo

#: Archivo donde el cliente lee las reglas.
RUTA_CLIENTE = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "shared"
    / "contrato"
    / "reglas.json"
)


def escribir(ruta: Path = RUTA_CLIENTE) -> Path:
    """Guarda el contrato en el archivo que lee el cliente."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(contrato_completo(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return ruta


def main() -> int:
    if "--escribir" in sys.argv:
        ruta = escribir()
        print(f"Contrato escrito en {ruta}")
        return 0
    print(json.dumps(contrato_completo(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
