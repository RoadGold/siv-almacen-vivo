"""Endpoints de reportes e indicadores (plan §5.7)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.services import reportes as servicio

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get("/ventas")
def ventas(
    desde: date | None = None,
    hasta: date | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> dict:
    """Ventas del periodo, por día, producto, categoría y usuario."""
    return {
        "periodo": servicio.ventas_por_periodo(db, desde=desde, hasta=hasta),
        "por_producto": servicio.ventas_por_producto(db, desde=desde, hasta=hasta),
        "por_categoria": servicio.ventas_por_categoria(db, desde=desde, hasta=hasta),
        "por_usuario": servicio.ventas_por_usuario(db, desde=desde, hasta=hasta),
    }


@router.get("/abastecimientos")
def abastecimientos(
    desde: date | None = None,
    hasta: date | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    return servicio.abastecimientos_por_proveedor(db, desde=desde, hasta=hasta)


@router.get("/costos")
def costos(
    producto_id: int | None = None,
    proveedor_id: int | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    return servicio.historico_de_costos(db, producto_id=producto_id, proveedor_id=proveedor_id)


@router.get("/inventario")
def inventario(
    almacen_id: int | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Inventario valorizado a costo promedio."""
    return servicio.inventario_valorizado(db, almacen_id=almacen_id)


@router.get("/inventario-por-lote")
def inventario_por_lote(
    producto_id: int | None = None,
    almacen_id: int | None = None,
    solo_con_stock: bool = Query(default=False),
    limite: int = Query(default=200, ge=1, le=1000),
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Inventario desglosado por lote (stock, costo y precio de cada lote)."""
    return servicio.inventario_por_lote(
        db,
        producto_id=producto_id,
        almacen_id=almacen_id,
        solo_con_stock=solo_con_stock,
        limite=limite,
    )


@router.get("/ventas-por-lote")
def ventas_por_lote(
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(default=200, ge=1, le=1000),
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Ventas y rentabilidad por lote."""
    return servicio.ventas_por_lote(db, desde=desde, hasta=hasta, limite=limite)


@router.get("/margen")
def margen(
    desde: date | None = None,
    hasta: date | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> dict:
    """Margen bruto estimado (ventas − costo de mercadería vendida)."""
    return servicio.margen_bruto(db, desde=desde, hasta=hasta)


@router.get("/ventas/exportar")
def exportar_ventas(
    desde: date | None = None,
    hasta: date | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.REPORTES_VER)),
    db: Session = Depends(get_db),
) -> Response:
    contenido = servicio.exportar_ventas_csv(db, desde=desde, hasta=hasta)
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ventas-siv.csv"'},
    )
