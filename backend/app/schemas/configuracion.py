"""Esquemas de la configuración del negocio y de la caja.

La configuración se guardaba como texto libre: cualquier cosa entraba, incluso
un nombre de 500 caracteres o un RUC «abc», y todo eso iba al ticket impreso.
Ahora cada clave tiene su regla.

El servicio (`app/services/configuracion.py`) conserva la lista de claves y los
valores por defecto: este schema solo define qué es válido.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: RUC peruano: 11 dígitos.
REGLAS_RUC = re.compile(r"^\d{11}$")


def _validar_ruc(valor: str) -> str:
    """El RUC del negocio, si se informa, tiene que ser de 11 dígitos."""
    limpio = valor.strip()
    if limpio == "":
        return ""
    if not REGLAS_RUC.match(limpio):
        raise ValueError("El RUC debe tener 11 dígitos.")
    return limpio


def _validar_limite(valor: str) -> str:
    """Los límites de descuento son números que no pueden ser negativos."""
    limpio = valor.strip()
    if limpio == "":
        return "0"
    try:
        numero = float(limpio)
    except ValueError as error:
        raise ValueError("El límite debe ser un número.") from error
    if numero < 0:
        raise ValueError("El límite no puede ser negativo.")
    return limpio


class ConfiguracionIn(BaseModel):
    """Configuración que se quiere guardar.

    Solo se guardan las claves conocidas: las demás se ignoran.
    """

    model_config = ConfigDict(extra="ignore")

    negocio_nombre: str | None = Field(default=None, max_length=120)
    negocio_ruc: str | None = Field(default=None, max_length=20)
    negocio_direccion: str | None = Field(default=None, max_length=240)
    negocio_telefono: str | None = Field(default=None, max_length=40)
    ticket_pie: str | None = Field(default=None, max_length=200)
    ticket_mostrar_precio_original: str | None = Field(default=None, max_length=3)
    ticket_mostrar_qr: str | None = Field(default=None, max_length=3)
    ticket_ancho: str | None = Field(default=None, max_length=3)
    venta_descuento_maximo_porcentaje: str | None = Field(default=None, max_length=20)
    venta_descuento_maximo_monto: str | None = Field(default=None, max_length=20)

    @field_validator("negocio_ruc", mode="before")
    @classmethod
    def _ruc(cls, v: Any) -> Any:
        return _validar_ruc(str(v)) if v is not None else None

    @field_validator("ticket_mostrar_precio_original", "ticket_mostrar_qr", mode="before")
    @classmethod
    def _booleano(cls, v: Any) -> Any:
        if v is None:
            return None
        limpio = str(v).strip().lower()
        if limpio in {"si", "sí", "yes", "true", "1", "x"}:
            return "si"
        if limpio in {"no", "false", "0"}:
            return "no"
        raise ValueError("El valor debe ser «si» o «no».")

    @field_validator("ticket_ancho", mode="before")
    @classmethod
    def _ancho(cls, v: Any) -> Any:
        if v is None:
            return None
        limpio = str(v).strip()
        if limpio not in {"58", "80"}:
            raise ValueError("El ancho del ticket debe ser 58 o 80.")
        return limpio

    @field_validator(
        "venta_descuento_maximo_porcentaje", "venta_descuento_maximo_monto", mode="before"
    )
    @classmethod
    def _limite(cls, v: Any) -> Any:
        return _validar_limite(str(v)) if v is not None else None
