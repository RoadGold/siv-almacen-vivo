"""Esquemas de autenticación y usuarios."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=4, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: "UsuarioOut"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    usuario: str
    activo: bool
    roles: list[str] = Field(default_factory=list)
    permisos: list[str] = Field(default_factory=list)
    ultimo_acceso: datetime | None = None


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    usuario: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=6, max_length=200)
    rol: str = Field(default="vendedor", max_length=50)
    activo: bool = True


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=6, max_length=200)
    activo: bool | None = None
    rol: str | None = Field(default=None, max_length=50)


TokenResponse.model_rebuild()
