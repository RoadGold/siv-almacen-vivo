"""Instalación inicial de SIV · Almacén Vivo (Windows / Linux / macOS).

Uso:
    python scripts/instalar/instalar.py --usuario admin --password mi-clave-segura
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.cli.instalar import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
