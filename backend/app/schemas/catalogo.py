"""Esquemas de catálogo: unidades, categorías, marcas, productos, presentaciones."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.unidades import dec


class UnidadMedidaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    dimension: str
    paso_minimo: int
    activo: bool


class UnidadMedidaCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=60)
    dimension: str = Field(pattern="^(UNIDAD|PESO|VOLUMEN)$")
    paso_minimo: int = Field(default=1, ge=1)


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    activo: bool


class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class MarcaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    activo: bool


class MarcaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class PresentacionIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    factor_base: Decimal = Field(gt=0)
    precio_venta: Decimal = Field(default=Decimal("0"), ge=0)
    costo_referencia: Decimal = Field(default=Decimal("0"), ge=0)
    codigo_barras: str | None = Field(default=None, max_length=64)
    es_compra: bool = True
    es_venta: bool = True
    permite_fraccion: bool = False

    @field_validator("factor_base", "precio_venta", "costo_referencia", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return dec(v)


class PresentacionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    factor_base: Decimal | None = Field(default=None, gt=0)
    precio_venta: Decimal | None = Field(default=None, ge=0)
    costo_referencia: Decimal | None = Field(default=None, ge=0)
    codigo_barras: str | None = Field(default=None, max_length=64)
    es_compra: bool | None = None
    es_venta: bool | None = None
    permite_fraccion: bool | None = None
    activo: bool | None = None

    @field_validator("factor_base", "precio_venta", "costo_referencia", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return None if v is None else dec(v)


class PresentacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int | None = None
    nombre: str
    factor_base: str
    precio_venta: str
    costo_referencia: str = "0"
    codigo_barras: str | None = None
    es_compra: bool
    es_venta: bool
    permite_fraccion: bool
    activo: bool


class ProductoIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    categoria_id: int | None = None
    marca_id: int | None = None
    unidad_base_id: int
    stock_minimo_base: Decimal = Field(default=Decimal("0"), ge=0)
    permite_fraccion: bool = False
    activo: bool = True
    presentaciones: list[PresentacionIn] = Field(default_factory=list)

    @field_validator("stock_minimo_base", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return dec(v)


class ProductoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    categoria_id: int | None = None
    marca_id: int | None = None
    stock_minimo_base: Decimal | None = Field(default=None, ge=0)
    permite_fraccion: bool | None = None
    activo: bool | None = None

    @field_validator("stock_minimo_base", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return None if v is None else dec(v)


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_id: int | None = None
    categoria: str | None = None
    marca_id: int | None = None
    marca: str | None = None
    unidad_base_id: int
    unidad_base: str | None = None
    stock_minimo_base: str = "0"
    permite_fraccion: bool = False
    activo: bool = True
    created_at: datetime | None = None
    presentaciones: list[PresentacionOut] = Field(default_factory=list)


class ProductoFicha(ProductoOut):
    """Ficha viva: producto + existencias + últimos movimientos."""

    existencias: list["ExistenciaResumen"] = Field(default_factory=list)
    proveedores: list["ProveedorProductoResumen"] = Field(default_factory=list)
    ultimo_costo: str | None = None
    movimientos_recientes: list["MovimientoResumen"] = Field(default_factory=list)


class ExistenciaResumen(BaseModel):
    almacen_id: int
    almacen: str | None = None
    cantidad_base: str = "0"
    costo_promedio_base: str = "0"
    presentacion_principal: str | None = None
    cantidad_presentacion: str | None = None
    unidad_base: str | None = None


class ProveedorProductoResumen(BaseModel):
    proveedor_id: int
    proveedor: str
    habitual: bool = False
    ultimo_costo: str | None = None
    ultima_fecha_compra: str | None = None


class MovimientoResumen(BaseModel):
    id: int
    tipo: str
    cantidad_base_signed: str
    saldo_base_despues: str
    referencia: str | None = None
    origen_tipo: str | None = None
    origen_id: int | None = None
    usuario: str | None = None
    created_at: datetime | None = None


ProductoFicha.model_rebuild()
