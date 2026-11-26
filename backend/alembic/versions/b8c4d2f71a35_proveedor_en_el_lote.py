"""proveedor en el lote de inventario

Revision ID: b8c4d2f71a35
Revises: f3a81e7b9012
Create Date: 2026-11-26 09:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c4d2f71a35"
down_revision: str | None = "f3a81e7b9012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # El lote debe recordar a quién se le compró la mercadería: sin este dato
    # no se puede atribuir la venta de un lote a su proveedor (histórico de
    # ganancias por proveedor).
    op.add_column(
        "lotes_inventario",
        sa.Column("proveedor_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_lotes_inventario_proveedor_id",
        "lotes_inventario",
        ["proveedor_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_lotes_inventario_proveedor_id",
        "lotes_inventario",
        "proveedores",
        ["proveedor_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Los lotes que vienen de un ingreso real toman el proveedor de ese ingreso.
    op.execute(
        """
        UPDATE lotes_inventario l
           SET proveedor_id = a.proveedor_id
          FROM abastecimientos a
         WHERE l.abastecimiento_id = a.id
           AND a.proveedor_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_lotes_inventario_proveedor_id", "lotes_inventario")
    op.drop_index("ix_lotes_inventario_proveedor_id", table_name="lotes_inventario")
    op.drop_column("lotes_inventario", "proveedor_id")
