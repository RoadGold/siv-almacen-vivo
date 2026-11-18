"""Errores de dominio y traducción a respuestas HTTP coherentes."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.domain.unidades import ErrorNegocio

logger = logging.getLogger("siv.errores")

# Traducción de los mensajes de validación de Pydantic al idioma del sistema.
TRADUCCIONES = {
    "Input should be greater than 0": "debe ser mayor que cero",
    "Input should be greater than or equal to 0": "no puede ser negativo",
    "Input should be less than or equal to 0": "no puede ser cero",
    "Input should be a valid string": "debe ser un texto",
    "Input should be a valid integer": "debe ser un número entero",
    "Input should be a valid number": "debe ser un número",
    "Input should be a valid list": "debe ser una lista",
    "Input should be a valid dictionary": "debe ser un conjunto de datos",
    "Field required": "es obligatorio",
    "String should match pattern": "no tiene el formato esperado",
    "Value is not a valid email address": "no es un correo electrónico válido",
    "ensure this value is greater than or equal to": "no puede ser menor que",
    "ensure this value is less than or equal to": "no puede ser mayor que",
    "value is not a valid decimal": "no es un número válido",
}

# Nombre legible de los campos que más se usan.
NOMBRES_CAMPO = {
    "cantidad": "La cantidad",
    "cantidad_base": "La cantidad",
    "costo_unitario": "El costo unitario",
    "precio_venta": "El precio de venta",
    "precio_total": "El total de la línea",
    "precio_unitario": "El precio unitario",
    "motivo": "El motivo",
    "motivo_precio": "El motivo",
    "codigo": "El código",
    "nombre": "El nombre",
    "usuario": "El usuario",
    "password": "La contraseña",
    "rol": "El rol",
    "documento": "El documento",
    "observaciones": "Las observaciones",
    "cliente": "El cliente",
    "forma_pago": "La forma de pago",
    "monto_recibido": "El monto recibido",
    "presentacion_id": "La presentación",
    "producto_id": "El producto",
    "proveedor_id": "El proveedor",
    "lote_id": "El lote",
    "almacen_id": "El almacén",
}


def _sanear(valor: Any) -> Any:
    """Convierte a texto lo que JSON no sabe serializar (Decimal, fecha…)."""
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {clave: _sanear(dato) for clave, dato in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_sanear(dato) for dato in valor]
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    return str(valor)


def _mensaje_de_validacion(errores: list[dict[str, Any]]) -> str:
    """Construye un mensaje legible a partir del primer error de validación."""
    if not errores:
        return "Los datos enviados no son válidos."
    primero = errores[0]
    campo = str(primero.get("loc", ["", ""])[-1])
    nombre = NOMBRES_CAMPO.get(campo)
    detalle = str(primero.get("msg", "no es válido"))
    # Pydantic envuelve los errores de valor propio con este prefijo.
    if detalle.startswith("Value error, "):
        detalle = detalle[len("Value error, ") :]
    for original, traduccion in TRADUCCIONES.items():
        if detalle.startswith(original):
            detalle = traduccion + detalle[len(original) :]
            break
    if nombre:
        return f"{nombre} {detalle}."
    return f"Los datos enviados no son válidos: {detalle}."


class ErrorApi(Exception):
    def __init__(
        self,
        codigo: str,
        mensaje: str,
        *,
        status_code: int = 400,
        detalle: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.status_code = status_code
        self.detalle = detalle or {}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErrorNegocio)
    async def _negocio(_: Request, exc: ErrorNegocio) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "codigo": exc.codigo,
                    "mensaje": exc.mensaje,
                    "detalle": exc.detalle,
                }
            },
        )

    @app.exception_handler(ErrorApi)
    async def _api(_: Request, exc: ErrorApi) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "codigo": exc.codigo,
                    "mensaje": exc.mensaje,
                    "detalle": exc.detalle,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Los detalles de Pydantic pueden traer Decimal o fechas: se sanean para
        # que la respuesta se pueda serializar (si no, el manejador se cae y el
        # usuario ve un error 500 en vez de su mensaje real).
        errores = _sanear(exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "codigo": "validacion",
                    "mensaje": _mensaje_de_validacion(errores),
                    "detalle": {"campos": errores},
                }
            },
        )

    @app.exception_handler(IntegrityError)
    async def _integridad(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Error de integridad: %s", exc.orig)
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "codigo": "conflicto_datos",
                    "mensaje": "La operación entra en conflicto con datos existentes.",
                    "detalle": {},
                }
            },
        )

    @app.exception_handler(Exception)
    async def _generico(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error no controlado: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "codigo": "error_interno",
                    "mensaje": "Ocurrió un error inesperado. Intente nuevamente.",
                    "detalle": {},
                }
            },
        )
