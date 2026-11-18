"""Endpoints de los lotes de inventario."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.domain.unidades import ErrorNegocio, dec
from app.services import lotes as servicio

router = APIRouter(prefix="/lotes", tags=["Lotes de inventario"])


class PrecioLoteIn(BaseModel):
    presentacion_id: int
    precio: Decimal = Field(ge=0)
    motivo: str | None = Field(default=None, max_length=200)


@router.get("/producto/{producto_id}")
def listar_lotes(
    producto_id: int,
    almacen_id: int | None = None,
    solo_con_stock: bool = Query(default=False),
    _: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Lotes de un producto con su stock, costo y precios de venta."""
    return servicio.listar_lotes(
        db, producto_id, almacen_id=almacen_id, solo_con_stock=solo_con_stock
    )


@router.patch("/{lote_id}/precios")
def actualizar_precio(
    lote_id: int,
    datos: PrecioLoteIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.PRECIOS_GESTIONAR)),
    db: Session = Depends(get_db),
) -> dict:
    """Cambia el precio de venta de una presentación dentro de un lote."""
    resultado = servicio.actualizar_precio_lote(
        db,
        lote_id,
        datos.presentacion_id,
        dec(datos.precio),
        usuario.id,
        datos.motivo,
    )
    db.commit()
    return resultado


@router.get("/{lote_id}")
def obtener(
    lote_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_VER)),
    db: Session = Depends(get_db),
) -> dict:
    lote = servicio.obtener_lote(db, lote_id)
    from app.db.models import Producto

    producto = db.get(Producto, lote.producto_id)
    return servicio._lote_a_dict(lote, producto)


__all__ = ["router"]
