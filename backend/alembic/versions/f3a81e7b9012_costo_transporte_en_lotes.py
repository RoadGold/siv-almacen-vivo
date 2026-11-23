"""costo de transporte en recepcion y lotes

Revision ID: f3a81e7b9012
Revises: c7e91b4d2a06
Create Date: 2026-11-22 14:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a81e7b9012"
down_revision: str | None = "c7e91b4d2a06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "detalle_abastecimientos",
        sa.Column(
            "costo_transporte",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "lotes_inventario",
        sa.Column(
            "costo_transporte",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("lotes_inventario", "costo_transporte")
    op.drop_column("detalle_abastecimientos", "costo_transporte")
