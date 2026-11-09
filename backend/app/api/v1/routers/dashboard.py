"""Endpoints de dashboard y operación inicial."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.schemas.inventario import DashboardResumen
from app.services import existencias as servicio

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumen", response_model=DashboardResumen)
def resumen(
    almacen_id: int | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> DashboardResumen:
    return DashboardResumen(**servicio.dashboard_resumen(db, almacen_id=almacen_id))
