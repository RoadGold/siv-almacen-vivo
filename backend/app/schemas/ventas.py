"""Esquemas de ventas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.unidades import dec


class LineaVentaIn(BaseModel):
    producto_id: int
    presentacion_id: int
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal | None = Field(default=None, ge=0)

    @field_validator("cantidad", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return dec(v)

    @field_validator("precio_unitario", mode="before")
    @classmethod
    def _precio_a_decimal(cls, v):
        return None if v is None else dec(v)


class VentaIn(BaseModel):
    almacen_id: int | None = None
    fecha: date | None = None
    cliente: str | None = Field(default=None, max_length=160)
    observaciones: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=80)
    lineas: list[LineaVentaIn] = Field(min_length=1)

    @field_validator("lineas")
    @classmethod
    def _lineas_no_vacias(cls, v):
        if not v:
            raise ValueError("La venta debe tener al menos una línea.")
        return v


class LineaCalculadaVenta(BaseModel):
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    presentacion_id: int
    presentacion_nombre: str
    cantidad: str
    factor_snapshot: str
    cantidad_base: str
    unidad_base: str
    precio_unitario: str
    subtotal: str
    stock_actual_base: str
    stock_resultante_base: str
    costo_base: str | None = None
    alerta: str | None = None


class PrevisualizacionVentaOut(BaseModel):
    total: str
    costo_estimado: str
    lineas: list[LineaCalculadaVenta]
    alertas: list[str] = Field(default_factory=list)


class DetalleVentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    presentacion_id: int
    cantidad: str
    factor_snapshot: str
    cantidad_base: str
    precio_unitario: str
    subtotal: str
    costo_total_linea: str = "0"
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    presentacion_nombre: str | None = None


class VentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    almacen_id: int
    fecha: date
    estado: str
    total: str
    costo_total: str = "0"
    cliente: str | None = None
    observaciones: str | None = None
    usuario: str | None = None
    created_at: datetime | None = None
    detalles: list[DetalleVentaOut] = Field(default_factory=list)


class AnulacionVentaIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)
