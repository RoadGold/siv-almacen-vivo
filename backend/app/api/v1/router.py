"""Agregación de routers de la API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    abastecimientos,
    admin,
    auth,
    catalogo,
    configuracion,
    dashboard,
    impresora,
    inventario,
    proveedores,
    reportes,
    ventas,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(catalogo.router)
api_router.include_router(proveedores.router)
api_router.include_router(abastecimientos.router)
api_router.include_router(ventas.router)
api_router.include_router(inventario.router)
api_router.include_router(dashboard.router)
api_router.include_router(reportes.router)
api_router.include_router(configuracion.router)
api_router.include_router(impresora.router)
api_router.include_router(admin.router)
