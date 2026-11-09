"""Limpia los datos de la base de desarrollo (mantiene el esquema)."""

from __future__ import annotations

import sys

from sqlalchemy import text

from app.db.base import Base
from app.db import models  # noqa: F401  (registra las tablas)
from app.db.session import engine

EXCLUIDAS = {"alembic_version"}


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    tablas = [
        tabla
        for tabla in Base.metadata.sorted_tables
        if tabla.name not in EXCLUIDAS
    ]
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE "
                + ", ".join(f'"{t.name}"' for t in tablas)
                + " RESTART IDENTITY CASCADE"
            )
        )
    print(f"✔ Datos eliminados de {len(tablas)} tablas.")


if __name__ == "__main__":
    sys.exit(main())
