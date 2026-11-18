"""Esquemas de los lotes de inventario."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class PrecioLoteIn(BaseModel):
    """Cambio del precio de venta de un lote."""

    presentacion_id: int
    precio: Decimal = Field(ge=0)
    motivo: str | None = Field(default=None, max_length=200)
