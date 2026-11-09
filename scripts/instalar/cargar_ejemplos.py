"""Carga de datos de ejemplo para explorar el sistema.

Uso:
    python scripts/instalar/cargar_ejemplos.py

Los datos son ficticios (nunca datos reales de un negocio).
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.cli.datos_ejemplo import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
