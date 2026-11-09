"""Configuración de pruebas: base de datos de pruebas y cliente HTTP."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import (
    Almacen,
    Categoria,
    Dimension,
    Rol,
    RolNombre,
    UnidadMedida,
    Usuario,
    UsuarioRol,
)
from app.db.session import get_db

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://siv:siv@127.0.0.1:5433/siv_almacen_vivo_test",
)

engine = create_engine(TEST_DATABASE_URL, future=True, pool_pre_ping=True)


@pytest.fixture(scope="session", autouse=True)
def _preparar_base() -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def cliente(db: Session) -> Iterator[TestClient]:
    from app.main import app

    def _get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def almacen(db: Session) -> Almacen:
    existente = db.execute(
        select(Almacen).where(Almacen.es_principal.is_(True))
    ).scalar_one_or_none()
    if existente is not None:
        return existente
    almacen = Almacen(nombre="Almacén principal", activo=True, es_principal=True)
    db.add(almacen)
    db.flush()
    return almacen


@pytest.fixture
def unidades(db: Session) -> dict[str, UnidadMedida]:
    resultado = {}
    for codigo, nombre, dimension in (
        ("UND", "Unidad", Dimension.UNIDAD),
        ("GR", "Gramo", Dimension.PESO),
        ("ML", "Mililitro", Dimension.VOLUMEN),
    ):
        existente = db.execute(
            select(UnidadMedida).where(UnidadMedida.codigo == codigo)
        ).scalar_one_or_none()
        if existente is None:
            existente = UnidadMedida(
                codigo=codigo, nombre=nombre, dimension=dimension, paso_minimo=1
            )
            db.add(existente)
            db.flush()
        resultado[codigo] = existente
    return resultado


@pytest.fixture
def categoria(db: Session) -> Categoria:
    existente = db.execute(
        select(Categoria).where(Categoria.nombre == "Abarrotes")
    ).scalar_one_or_none()
    if existente is not None:
        return existente
    categoria = Categoria(nombre="Abarrotes")
    db.add(categoria)
    db.flush()
    return categoria


@pytest.fixture
def roles(db: Session) -> dict[str, Rol]:
    resultado = {}
    for nombre, descripcion in (
        (RolNombre.ADMINISTRADOR.value, "Total"),
        (RolNombre.VENDEDOR.value, "Punto de venta"),
    ):
        existente = db.execute(select(Rol).where(Rol.nombre == nombre)).scalar_one_or_none()
        if existente is None:
            existente = Rol(nombre=nombre, descripcion=descripcion)
            db.add(existente)
            db.flush()
        resultado[nombre] = existente
    return resultado


@pytest.fixture
def admin(db: Session, roles: dict[str, Rol]) -> Usuario:
    usuario = Usuario(
        nombre="Administrador",
        usuario="admin",
        password_hash=hash_password("clave-admin"),
        activo=True,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=roles["administrador"].id))
    db.flush()
    return usuario


@pytest.fixture
def vendedor(db: Session, roles: dict[str, Rol]) -> Usuario:
    usuario = Usuario(
        nombre="Vendedor",
        usuario="vendedor",
        password_hash=hash_password("clave-vendedor"),
        activo=True,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=roles["vendedor"].id))
    db.flush()
    return usuario


def _token(cliente: TestClient, usuario: str, password: str) -> str:
    respuesta = cliente.post(
        "/api/v1/auth/login", json={"usuario": usuario, "password": password}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


@pytest.fixture
def token_admin(cliente: TestClient, admin: Usuario) -> str:
    return _token(cliente, "admin", "clave-admin")


@pytest.fixture
def token_vendedor(cliente: TestClient, vendedor: Usuario) -> str:
    return _token(cliente, "vendedor", "clave-vendedor")


@pytest.fixture
def cabeceras_admin(token_admin: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def cabeceras_vendedor(token_vendedor: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_vendedor}"}


@pytest.fixture
def clave_idempotencia() -> str:
    return f"test-{uuid.uuid4()}"
