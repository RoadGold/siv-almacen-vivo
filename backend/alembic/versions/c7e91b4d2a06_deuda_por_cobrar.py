"""deuda por cobrar en la venta

Revision ID: c7e91b4d2a06
Revises: eb57af921c95
Create Date: 2026-11-18 11:05:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op



revision: str = 'c7e91b4d2a06'
down_revision: str | None = 'eb57af921c95'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Importe que quedó sin cobrar cuando el efectivo no cubrió el total de la
    # venta. Antes se perdía: `vuelto` valía cero y no había forma de saber que
    # faltaba dinero.
    op.add_column(
        'ventas',
        sa.Column('deuda', sa.Numeric(precision=14, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ventas', 'deuda')
