"""Endpoints de autenticación."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, permisos_usuario
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.models import Usuario, UsuarioRol
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _usuario_out(usuario: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        usuario=usuario.usuario,
        activo=usuario.activo,
        roles=[ur.rol.nombre for ur in usuario.roles],
        permisos=sorted(permisos_usuario(usuario)),
        ultimo_acceso=usuario.ultimo_acceso,
    )


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    usuario = db.execute(
        select(Usuario)
        .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
        .where(Usuario.usuario == datos.usuario.strip().lower())
    ).scalar_one_or_none()
    if usuario is None or not verify_password(datos.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="El usuario está desactivado."
        )
    usuario.ultimo_acceso = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token(
        str(usuario.id), extra={"nombre": usuario.nombre, "usuario": usuario.usuario}
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        usuario=_usuario_out(usuario),
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)) -> UsuarioOut:
    return _usuario_out(usuario)


@router.post("/logout")
def logout(usuario: Usuario = Depends(get_current_user)) -> dict[str, str]:
    """El token es sin estado; el cierre de sesión real ocurre en el cliente."""
    return {"mensaje": "Sesión cerrada."}
