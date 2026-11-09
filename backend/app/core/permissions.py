"""Permisos por rol (plan §5.8 · matriz inicial de permisos)."""

from __future__ import annotations

from enum import StrEnum


class Permiso(StrEnum):
    CATALOGO_VER = "catalogo.ver"
    CATALOGO_GESTIONAR = "catalogo.gestionar"
    PROVEEDORES_VER = "proveedores.ver"
    PROVEEDORES_GESTIONAR = "proveedores.gestionar"
    ABASTECIMIENTOS_VER = "abastecimientos.ver"
    ABASTECIMIENTOS_CREAR = "abastecimientos.crear"
    ABASTECIMIENTOS_ANULAR = "abastecimientos.anular"
    VENTAS_VER = "ventas.ver"
    VENTAS_CREAR = "ventas.crear"
    VENTAS_ANULAR = "ventas.anular"
    INVENTARIO_VER = "inventario.ver"
    INVENTARIO_AJUSTAR = "inventario.ajustar"
    PRECIOS_GESTIONAR = "precios.gestionar"
    REPORTES_VER = "reportes.ver"
    REPORTES_TODOS = "reportes.todos"
    ADMIN_USUARIOS = "admin.usuarios"
    ADMIN_RESPALDOS = "admin.respaldos"
    ADMIN_AUDITORIA = "admin.auditoria"


PERMISOS_ADMIN = {p.value for p in Permiso}

PERMISOS_VENDEDOR = {
    Permiso.CATALOGO_VER.value,
    Permiso.PROVEEDORES_VER.value,
    Permiso.ABASTECIMIENTOS_VER.value,
    Permiso.VENTAS_VER.value,
    Permiso.VENTAS_CREAR.value,
    Permiso.INVENTARIO_VER.value,
    Permiso.REPORTES_VER.value,
}

PERMISOS_POR_ROL: dict[str, set[str]] = {
    "administrador": PERMISOS_ADMIN,
    "vendedor": PERMISOS_VENDEDOR,
}


def permisos_de_rol(rol_nombre: str) -> set[str]:
    return set(PERMISOS_POR_ROL.get(rol_nombre, set()))
