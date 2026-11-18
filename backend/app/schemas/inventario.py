"""Esquemas de inventario: existencias, kardex, ajustes y dashboard."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.unidades import decimal_ingreso


class ExistenciaOut(BaseModel):
    producto_id: int
    almacen_id: int
    codigo: str | None = None
    producto: str | None = None
    categoria: str | None = None
    unidad_base: str | None = None
    cantidad_base: str = "0"
    costo_promedio_base: str = "0"
    valor_costo: str = "0"
    stock_minimo_base: str = "0"
    presentacion_principal: str | None = None
    cantidad_presentacion: str | None = None
    estado: str = "disponible"
    ubicacion: str | None = None


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    almacen_id: int
    almacen: str | None = None
    tipo: str
    cantidad_base_signed: str
    saldo_base_despues: str
    costo_unitario_base: str = "0"
    origen_tipo: str | None = None
    origen_id: int | None = None
    referencia: str | None = None
    usuario: str | None = None
    lote_id: int | None = None
    created_at: datetime | None = None


class AjusteIn(BaseModel):
    almacen_id: int
    producto_id: int
    cantidad_base: Decimal = Field(description="Positivo suma, negativo resta.")
    motivo: str = Field(min_length=5, max_length=500)
    lote_id: int | None = Field(
        default=None,
        description="Lote afectado. Obligatorio si el producto tiene varios lotes con stock.",
    )

    @field_validator("cantidad_base", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return decimal_ingreso(v)


class AjusteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    almacen_id: int
    producto_id: int
    tipo: str
    cantidad_base: str
    motivo: str
    estado: str
    created_at: datetime | None = None


class DashboardResumen(BaseModel):
    fecha: str
    ventas_dia: str = "0"
    cantidad_ventas_dia: int = 0
    ingresos_dia: str = "0"
    productos_agotados: int = 0
    productos_bajo_minimo: int = 0
    valor_inventario_costo: str = "0"
    total_productos: int = 0
    ultimo_ingreso: str | None = None
    ultima_venta: str | None = None


class RadarReposicionItem(BaseModel):
    producto_id: int
    codigo: str
    producto: str
    unidad_base: str | None = None
    cantidad_base: str = "0"
    stock_minimo_base: str = "0"
    cantidad_presentacion: str | None = None
    presentacion_principal: str | None = None
    proveedor_sugerido: str | None = None
    proveedor_id: int | None = None
    ultimo_costo: str | None = None
    prioridad: int = 0
    estado: str = "bajo_minimo"


class ConciliacionOut(BaseModel):
    fecha: str
    diferencias: list[dict] = Field(default_factory=list)
    existencias_negativas: list[dict] = Field(default_factory=list)
    detalle_movimientos: int = 0
    detalle_existencias: int = 0
