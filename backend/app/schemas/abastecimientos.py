"""Esquemas de abastecimiento (recepción de mercadería)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.unidades import decimal_ingreso


class LineaAbastecimientoIn(BaseModel):
    producto_id: int
    presentacion_id: int
    cantidad: Decimal = Field(gt=0)
    costo_unitario: Decimal = Field(ge=0)
    costo_transporte: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Gasto extra de transporte correspondiente a este lote.",
    )
    precio_venta: Decimal | None = Field(
        default=None,
        ge=0,
        description="Precio de venta del lote para esta presentación. Si se omite, "
        "se usa el precio vigente de la presentación.",
    )
    fecha_ingreso: date | None = Field(
        default=None, description="Fecha del lote (por defecto, la del ingreso)."
    )

    @field_validator("cantidad", "costo_unitario", "precio_venta", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return None if v is None else decimal_ingreso(v)

    @field_validator("costo_transporte", mode="before")
    @classmethod
    def _transporte_a_decimal(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return Decimal("0")
        return decimal_ingreso(v)


class AbastecimientoIn(BaseModel):
    proveedor_id: int
    almacen_id: int | None = None
    fecha: date | None = None
    documento: str | None = Field(default=None, max_length=60)
    observaciones: str | None = None
    lineas: list[LineaAbastecimientoIn] = Field(min_length=1)

    @field_validator("lineas")
    @classmethod
    def _lineas_no_vacias(cls, v):
        if not v:
            raise ValueError("El abastecimiento debe tener al menos una línea.")
        return v


class LineaCalculada(BaseModel):
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    presentacion_id: int
    presentacion_nombre: str
    cantidad: str
    factor_snapshot: str
    cantidad_base: str
    unidad_base: str
    costo_unitario: str
    costo_transporte: str = "0"
    subtotal: str
    stock_actual_base: str
    stock_resultante_base: str
    alerta: str | None = None


class PrevisualizacionOut(BaseModel):
    total: str
    lineas: list[LineaCalculada]
    alertas_stock_minimo: int = 0


class DetalleAbastecimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    presentacion_id: int
    cantidad: str
    factor_snapshot: str
    cantidad_base: str
    costo_unitario: str
    costo_transporte: str = "0"
    subtotal: str
    lote_id: int | None = None
    lote_codigo: str | None = None
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    presentacion_nombre: str | None = None


class AbastecimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    proveedor_id: int
    proveedor_nombre: str | None = None
    almacen_id: int
    fecha: date
    documento: str | None = None
    observaciones: str | None = None
    estado: str
    total: str
    usuario: str | None = None
    created_at: datetime | None = None
    detalles: list[DetalleAbastecimientoOut] = Field(default_factory=list)


class AnulacionIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)
