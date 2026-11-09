"""Errores de dominio y traducción a respuestas HTTP coherentes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.domain.unidades import ErrorNegocio

logger = logging.getLogger("siv.errores")


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
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "codigo": "validacion",
                    "mensaje": "Los datos enviados no son válidos.",
                    "detalle": {"campos": exc.errors()},
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
