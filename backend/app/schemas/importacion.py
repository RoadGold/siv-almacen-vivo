"""Esquemas de importación de catálogo e inventario inicial."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.unidades import decimal_ingreso


class LineaInventarioInicial(BaseModel):
    producto_id: int
    cantidad_base: Decimal = Field(gt=0)
    costo_unitario_base: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("cantidad_base", "costo_unitario_base", mode="before")
    @classmethod
    def _a_decimal(cls, v):
        return decimal_ingreso(v)


class InventarioInicialIn(BaseModel):
    almacen_id: int | None = None
    referencia: str = Field(default="Inventario inicial", max_length=120)
    lineas: list[LineaInventarioInicial] = Field(min_length=1)


class ResumenImportacion(BaseModel):
    filas: int = 0
    nuevos: int = 0
    actualizar: int = 0
    con_errores: int = 0
    con_avisos: int = 0
    con_stock_inicial: int = 0
    vinculos_proveedor: int = 0


class FilaImportadaOut(BaseModel):
    numero: int
    codigo: str = ""
    nombre: str = ""
    categoria: str = ""
    presentacion: str = ""
    factor_base: str = ""
    precio_venta: str = ""
    stock_inicial: str = ""
    proveedor_codigo: str = ""
    estado: str = "nuevo"
    mensajes: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)


class PrevisualizacionImportacion(BaseModel):
    resumen: ResumenImportacion
    filas: list[FilaImportadaOut]


class ResultadoImportacion(BaseModel):
    importadas: int = 0
    productos_creados: int = 0
    productos_actualizados: int = 0
    rechazadas: int = 0
    vinculos_proveedor: int = 0
    stock_inicial_aplicado: int = 0
    aplicadas: list[FilaImportadaOut] = Field(default_factory=list)
    errores: list[FilaImportadaOut] = Field(default_factory=list)
