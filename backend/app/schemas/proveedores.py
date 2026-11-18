"""Esquemas de proveedores."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.unidades import dec

#: RUC peruano: 11 dígitos.
REGLAS_RUC = re.compile(r"^\d{11}$")

#: Correo electrónico: la misma forma que revisa el cliente.
REGLAS_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validar_ruc(valor: str | None) -> str | None:
    """El RUC, si viene, tiene que ser de 11 dígitos."""
    if valor is None:
        return None
    limpio = valor.strip()
    if limpio == "":
        return None
    if not REGLAS_RUC.match(limpio):
        raise ValueError("El RUC debe tener 11 dígitos.")
    return limpio


def _validar_email(valor: str | None) -> str | None:
    """El correo, si viene, tiene que tener la forma de un correo."""
    if valor is None:
        return None
    limpio = valor.strip()
    if limpio == "":
        return None
    if not REGLAS_EMAIL.match(limpio):
        raise ValueError("El correo electrónico no tiene un formato válido.")
    return limpio


class ProveedorIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    razon_social: str = Field(min_length=1, max_length=200)
    nombre_comercial: str | None = Field(default=None, max_length=200)
    ruc: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=40)
    contacto: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=240)
    email: str | None = Field(default=None, max_length=120)
    observaciones: str | None = None
    activo: bool = True

    @field_validator("ruc", mode="before")
    @classmethod
    def _ruc(cls, v):
        return _validar_ruc(v if v is None else str(v))

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return _validar_email(v if v is None else str(v))


class ProveedorUpdate(BaseModel):
    """Cambios de un proveedor.

    Un campo que viene en `null` se **borra** (queda vacío); un campo que no
    viene en la petición se deja como estaba. Así vaciar el RUC en el formulario
    limpia el RUC de verdad.
    """

    razon_social: str | None = Field(default=None, min_length=1, max_length=200)
    nombre_comercial: str | None = Field(default=None, max_length=200)
    ruc: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=40)
    contacto: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=240)
    email: str | None = Field(default=None, max_length=120)
    observaciones: str | None = None
    activo: bool | None = None

    @field_validator("ruc", mode="before")
    @classmethod
    def _ruc(cls, v):
        return _validar_ruc(v if v is None else str(v))

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return _validar_email(v if v is None else str(v))


class ProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    razon_social: str
    nombre_comercial: str | None = None
    ruc: str | None = None
    telefono: str | None = None
    contacto: str | None = None
    direccion: str | None = None
    email: str | None = None
    observaciones: str | None = None
    activo: bool = True


class ProductoProveedorIn(BaseModel):
    producto_id: int
    proveedor_id: int
    habitual: bool = False
    presentacion_id: int | None = None
    observacion: str | None = None


class ProductoProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    proveedor_id: int
    habitual: bool
    presentacion_id: int | None = None
    ultimo_costo: str | None = None
    ultima_fecha_compra: date | None = None
    observacion: str | None = None


class ProductoProveedorDetalle(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    unidad_base: str | None = None
    presentacion_id: int | None = None
    presentacion_nombre: str | None = None
    factor_base: str | None = None
    ultimo_costo: str | None = None
    ultima_fecha_compra: date | None = None
    habitual: bool = False


class CostoHistoricoProveedor(BaseModel):
    producto_id: int
    producto: str
    proveedor_id: int
    proveedor: str
    presentacion: str
    costo_unitario: str
    fecha: str
    documento: str | None = None
    cantidad: str
