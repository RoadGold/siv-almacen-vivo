"""Dependencias de API: usuario actual, permisos y almacén por defecto."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import permisos_de_rol
from app.core.security import decode_access_token
from app.db.models import Almacen, Usuario, UsuarioRol
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debe iniciar sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o vencida.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    usuario_id = payload.get("sub")
    usuario = db.execute(
        select(Usuario)
        .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
        .where(Usuario.id == int(usuario_id))
    ).scalar_one_or_none()
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no disponible.",
        )
    return usuario


def permisos_usuario(usuario: Usuario) -> set[str]:
    permisos: set[str] = set()
    for usuario_rol in usuario.roles:
        permisos |= permisos_de_rol(usuario_rol.rol.nombre)
    return permisos


def requiere_permiso(permiso: str) -> Callable[..., Usuario]:
    """Dependencia que valida el permiso en el servidor (no solo ocultando botones)."""

    def _dep(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if permiso not in permisos_usuario(usuario):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene permiso para la acción «{permiso}».",
            )
        return usuario

    return _dep


def get_almacen_por_defecto(db: Session = Depends(get_db)) -> Almacen:
    almacen = db.execute(
        select(Almacen).where(Almacen.activo.is_(True)).order_by(Almacen.id)
    ).scalars().first()
    if almacen is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No hay un almacén activo configurado. Ejecute la instalación inicial.",
        )
    return almacen


def sesion_actual(request: Request) -> str | None:
    return request.headers.get("x-sesion")
