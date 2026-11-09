"""Esquemas comunes de API."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int = 0
    pagina: int = 1
    tamano: int = 20
    paginas: int = 0


class Mensaje(BaseModel):
    mensaje: str
    detalle: dict | None = None


class BaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ResumenProducto(BaseModel):
    """Vista ligera para el buscador y el carrito de venta."""

    id: int
    codigo: str
    nombre: str
    unidad_base: str
    stock_base: str = "0"
    presentaciones: list["PresentacionOut"] = Field(default_factory=list)


class PresentacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    factor_base: str
    precio_venta: str
    codigo_barras: str | None = None
    es_compra: bool = True
    es_venta: bool = True
    permite_fraccion: bool = False
    activo: bool = True
