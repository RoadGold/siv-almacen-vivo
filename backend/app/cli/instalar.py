"""Instalación inicial: rol, administrador, almacén, unidades y catálogos básicos.

Uso:
    python -m app.cli.instalar --usuario admin --password clave --nombre "Administrador"

Es idempotente: se puede volver a ejecutar sin duplicar datos.
"""

from __future__ import annotations

import argparse
import sys


def _preparar_consola() -> None:
    """Evita errores de codificación en la consola de Windows (cp1252)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


_preparar_consola()

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    Almacen,
    Categoria,
    Dimension,
    Marca,
    Rol,
    RolNombre,
    UnidadMedida,
    Usuario,
    UsuarioRol,
)
from app.db.session import SessionLocal

UNIDADES_BASE = [
    {"codigo": "UND", "nombre": "Unidad", "dimension": Dimension.UNIDAD, "paso_minimo": 1},
    {"codigo": "GR", "nombre": "Gramo", "dimension": Dimension.PESO, "paso_minimo": 1},
    {"codigo": "ML", "nombre": "Mililitro", "dimension": Dimension.VOLUMEN, "paso_minimo": 1},
    {"codigo": "KG", "nombre": "Kilogramo", "dimension": Dimension.PESO, "paso_minimo": 1000},
    {"codigo": "LT", "nombre": "Litro", "dimension": Dimension.VOLUMEN, "paso_minimo": 1000},
]

CATEGORIAS_BASE = [
    "Abarrotes",
    "Bebidas",
    "Lácteos",
    "Panadería",
    "Aseo del hogar",
    "Cuidado personal",
    "Snacks",
    "Granos y menestras",
]


def instalar(
    usuario_nombre: str = "admin",
    password: str = "cambiar-esta-clave",
    nombre: str = "Administrador",
    almacen: str = "Almacén principal",
    con_datos_base: bool = True,
) -> None:
    db = SessionLocal()
    try:
        # --- Roles ---------------------------------------------------------
        for rol_nombre, descripcion in (
            (RolNombre.ADMINISTRADOR, "Acceso total al sistema"),
            (RolNombre.VENDEDOR, "Opera el punto de venta"),
        ):
            rol = db.execute(
                select(Rol).where(Rol.nombre == rol_nombre.value)
            ).scalar_one_or_none()
            if rol is None:
                db.add(Rol(nombre=rol_nombre.value, descripcion=descripcion))
                db.flush()

        # --- Administrador -------------------------------------------------
        usuario = db.execute(
            select(Usuario).where(Usuario.usuario == usuario_nombre.strip().lower())
        ).scalar_one_or_none()
        if usuario is None:
            rol_admin = db.execute(
                select(Rol).where(Rol.nombre == RolNombre.ADMINISTRADOR.value)
            ).scalar_one()
            usuario = Usuario(
                nombre=nombre,
                usuario=usuario_nombre.strip().lower(),
                password_hash=hash_password(password),
                activo=True,
            )
            db.add(usuario)
            db.flush()
            db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol_admin.id))
            print(f"✔ Administrador creado: {usuario_nombre}")
        else:
            print(f"· El usuario «{usuario_nombre}» ya existe (no se modificó).")

        # --- Almacén -------------------------------------------------------
        almacen_principal = db.execute(
            select(Almacen).where(Almacen.es_principal.is_(True))
        ).scalar_one_or_none()
        if almacen_principal is None:
            almacen_principal = Almacen(nombre=almacen, activo=True, es_principal=True)
            db.add(almacen_principal)
            db.flush()
            print(f"✔ Almacén creado: {almacen}")
        else:
            print(f"· El almacén «{almacen_principal.nombre}» ya existe.")

        # --- Unidades y catálogos -----------------------------------------
        if con_datos_base:
            for datos in UNIDADES_BASE:
                existe = db.execute(
                    select(UnidadMedida).where(UnidadMedida.codigo == datos["codigo"])
                ).scalar_one_or_none()
                if existe is None:
                    db.add(UnidadMedida(**datos))
            for nombre_categoria in CATEGORIAS_BASE:
                existe = db.execute(
                    select(Categoria).where(Categoria.nombre == nombre_categoria)
                ).scalar_one_or_none()
                if existe is None:
                    db.add(Categoria(nombre=nombre_categoria))
            if db.execute(select(Marca).limit(1)).scalar_one_or_none() is None:
                db.add(Marca(nombre="Genérica"))
            print("✔ Unidades y categorías base verificados.")

        db.commit()
        print("✔ Instalación inicial completada.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Instalación inicial de SIV · Almacén Vivo")
    parser.add_argument("--usuario", default="admin")
    parser.add_argument("--password", default="cambiar-esta-clave")
    parser.add_argument("--nombre", default="Administrador")
    parser.add_argument("--almacen", default="Almacén principal")
    parser.add_argument(
        "--sin-datos-base",
        action="store_true",
        help="No crea unidades ni categorías por defecto.",
    )
    args = parser.parse_args()
    instalar(
        usuario_nombre=args.usuario,
        password=args.password,
        nombre=args.nombre,
        almacen=args.almacen,
        con_datos_base=not args.sin_datos_base,
    )


if __name__ == "__main__":
    sys.exit(main())
