"""Punto de entrada de la API SIV · Almacén Vivo."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("siv")

FRONTEND_DIR = Path(__file__).resolve().parents[1].parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("SIV · Almacén Vivo iniciando (%s)", settings.environment)
    yield
    logger.info("SIV · Almacén Vivo detenido")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API local de inventario, proveedores, abastecimiento y ventas. "
        "Los montos y cantidades viajan como cadenas decimales."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/api/salud", tags=["Sistema"])
def salud() -> JSONResponse:
    return JSONResponse(
        {
            "estado": "ok",
            "servicio": settings.app_name,
            "version": settings.app_version,
            "entorno": settings.environment,
            "moneda": settings.moneda,
        }
    )


if FRONTEND_DIR.exists():
    # Se sirven los archivos compilados del frontend y, para cualquier ruta
    # desconocida, el index.html (comportamiento típico de una aplicación de
    # una sola página). Las rutas de la API tienen prioridad.
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIR / "assets"),
        name="assets",
    )

    @app.get("/{ruta_completa:path}", include_in_schema=False)
    def interfaz(ruta_completa: str) -> FileResponse:
        if ruta_completa.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado."})
        archivo = FRONTEND_DIR / ruta_completa
        if archivo.is_file():
            return FileResponse(archivo)
        return FileResponse(FRONTEND_DIR / "index.html")
