"""Endpoints de configuración del negocio y de la caja."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.services import configuracion as servicio

router = APIRouter(prefix="/configuracion", tags=["Configuración"])


@router.get("")
def leer(
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Configuración vigente. La ven todos; solo el administrador la modifica."""
    return {
        "valores": servicio.obtener_todo(db),
        "descripciones": servicio.descripciones(),
    }


@router.put("")
def actualizar(
    datos: dict[str, Any],
    usuario: Usuario = Depends(requiere_permiso(Permiso.ADMIN_USUARIOS)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Guarda la configuración del negocio y de la caja."""
    try:
        valores = servicio.guardar(db, datos, usuario.id)
    except ValueError as error:
        from app.domain.unidades import ErrorNegocio

        raise ErrorNegocio(str(error)) from error
    db.commit()
    return {
        "valores": valores,
        "descripciones": servicio.descripciones(),
    }
