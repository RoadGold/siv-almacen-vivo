"""Carga de datos de ejemplo (nunca datos reales) para explorar el sistema.

Uso:
    python -m app.cli.datos_ejemplo

Crea un proveedor, un catálogo pequeño de abarrotes con sus presentaciones,
un abastecimiento confirmado y dos ventas. Es idempotente: si el código de
producto ya existe, no lo duplica.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select


def _preparar_consola() -> None:
    """Evita errores de codificación en la consola de Windows (cp1252)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


_preparar_consola()

from app.db.models import (
    Abastecimiento,
    Almacen,
    Categoria,
    Dimension,
    Marca,
    Producto,
    Proveedor,
    UnidadMedida,
    Usuario,
)
from app.db.session import SessionLocal
from app.services import abastecimientos as servicio_abastecimientos
from app.services import catalogo
from app.services import ventas as servicio_ventas

CATALOGO_EJEMPLO = [
    {
        "codigo": "AJO-001",
        "nombre": "Arroz a granel",
        "categoria": "Granos y menestras",
        "unidad": "GR",
        "stock_minimo": "10000",
        "permite_fraccion": True,
        "presentaciones": [
            {"nombre": "1 kg", "factor_base": "1000", "precio_venta": "5.00", "permite_fraccion": True},
            {"nombre": "saco 50 kg", "factor_base": "50000", "precio_venta": "180.00"},
        ],
    },
    {
        "codigo": "GAS-500",
        "nombre": "Gaseosa 500 ml",
        "categoria": "Bebidas",
        "unidad": "UND",
        "stock_minimo": "48",
        "presentaciones": [
            {"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"},
            {"nombre": "paquete x6", "factor_base": "6", "precio_venta": "13.50"},
            {"nombre": "caja x24", "factor_base": "24", "precio_venta": "48.00"},
        ],
    },
    {
        "codigo": "LEC-400",
        "nombre": "Leche entera 400 g",
        "categoria": "Lácteos",
        "unidad": "UND",
        "stock_minimo": "24",
        "presentaciones": [
            {"nombre": "unidad", "factor_base": "1", "precio_venta": "4.50"},
            {"nombre": "caja x24", "factor_base": "24", "precio_venta": "98.00"},
        ],
    },
    {
        "codigo": "ACE-900",
        "nombre": "Aceite vegetal 900 ml",
        "categoria": "Abarrotes",
        "unidad": "UND",
        "stock_minimo": "12",
        "presentaciones": [
            {"nombre": "unidad", "factor_base": "1", "precio_venta": "8.40"},
            {"nombre": "caja x12", "factor_base": "12", "precio_venta": "95.00"},
        ],
    },
    {
        "codigo": "DET-500",
        "nombre": "Detergente líquido 500 ml",
        "categoria": "Aseo del hogar",
        "unidad": "UND",
        "stock_minimo": "12",
        "presentaciones": [
            {"nombre": "unidad", "factor_base": "1", "precio_venta": "9.00"},
            {"nombre": "caja x12", "factor_base": "12", "precio_venta": "99.00"},
        ],
    },
]


def _unidad(db, codigo: str, nombre: str, dimension: Dimension, paso: int = 1) -> UnidadMedida:
    unidad = db.execute(
        select(UnidadMedida).where(UnidadMedida.codigo == codigo)
    ).scalar_one_or_none()
    if unidad is None:
        unidad = UnidadMedida(
            codigo=codigo, nombre=nombre, dimension=dimension, paso_minimo=paso
        )
        db.add(unidad)
        db.flush()
    return unidad


def cargar() -> None:
    db = SessionLocal()
    try:
        # --- Base mínima ---------------------------------------------------
        _unidad(db, "UND", "Unidad", Dimension.UNIDAD)
        _unidad(db, "GR", "Gramo", Dimension.PESO)
        _unidad(db, "ML", "Mililitro", Dimension.VOLUMEN)

        almacen = db.execute(
            select(Almacen).where(Almacen.es_principal.is_(True))
        ).scalar_one_or_none()
        if almacen is None:
            almacen = Almacen(nombre="Almacén principal", activo=True, es_principal=True)
            db.add(almacen)
            db.flush()

        marca = db.execute(select(Marca).limit(1)).scalar_one_or_none()
        if marca is None:
            marca = Marca(nombre="Genérica")
            db.add(marca)
            db.flush()

        # --- Proveedor ------------------------------------------------------
        proveedor = db.execute(
            select(Proveedor).where(Proveedor.codigo == "PRV-001")
        ).scalar_one_or_none()
        if proveedor is None:
            proveedor = Proveedor(
                codigo="PRV-001",
                razon_social="Mayorista Central SAC",
                nombre_comercial="Mayorista Central",
                ruc="20512345678",
                telefono="01 555 0123",
                contacto="Rosa Quispe",
                direccion="Av. Los Frutales 1200, Lima",
                activo=True,
            )
            db.add(proveedor)
            db.flush()
            print("✔ Proveedor de ejemplo creado: Mayorista Central SAC")

        # --- Catálogo -------------------------------------------------------
        productos: dict[str, Producto] = {}
        for definicion in CATALOGO_EJEMPLO:
            existente = db.execute(
                select(Producto).where(Producto.codigo == definicion["codigo"])
            ).scalar_one_or_none()
            if existente is not None:
                productos[definicion["codigo"]] = existente
                continue
            categoria = db.execute(
                select(Categoria).where(Categoria.nombre == definicion["categoria"])
            ).scalar_one_or_none()
            if categoria is None:
                categoria = Categoria(nombre=definicion["categoria"])
                db.add(categoria)
                db.flush()
            unidad = db.execute(
                select(UnidadMedida).where(UnidadMedida.codigo == definicion["unidad"])
            ).scalar_one()
            producto = catalogo.crear_producto(
                db,
                {
                    "codigo": definicion["codigo"],
                    "nombre": definicion["nombre"],
                    "categoria_id": categoria.id,
                    "marca_id": marca.id,
                    "unidad_base_id": unidad.id,
                    "stock_minimo_base": definicion["stock_minimo"],
                    "permite_fraccion": definicion.get("permite_fraccion", False),
                    "activo": True,
                    "presentaciones": definicion["presentaciones"],
                },
            )
            productos[definicion["codigo"]] = producto
            print(f"✔ Producto creado: {definicion['nombre']}")

        db.flush()

        # --- Abastecimiento inicial -----------------------------------------
        usuario = db.execute(
            select(Usuario).where(Usuario.activo.is_(True)).order_by(Usuario.id)
        ).scalars().first()
        if usuario is None:
            raise SystemExit(
                "No hay ningún usuario activo. Ejecute antes la instalación inicial "
                "(scripts/instalar/instalar.py)."
            )
        usuario_id = usuario.id

        from app.services import proveedores as servicio_proveedores

        lineas = []
        plan = [
            ("AJO-001", "saco 50 kg", "2", "170.00"),
            ("GAS-500", "caja x24", "3", "45.00"),
            ("LEC-400", "caja x24", "2", "92.00"),
            ("ACE-900", "caja x12", "2", "88.00"),
            ("DET-500", "caja x12", "1", "92.00"),
        ]
        for codigo, presentacion_nombre, cantidad, costo in plan:
            producto = productos[codigo]
            presentacion = next(
                p for p in producto.presentaciones if p.nombre == presentacion_nombre
            )
            servicio_proveedores.vincular_producto(
                db,
                producto_id=producto.id,
                proveedor_id=proveedor.id,
                habitual=True,
                presentacion_id=presentacion.id,
            )
            lineas.append(
                {
                    "producto_id": producto.id,
                    "presentacion_id": presentacion.id,
                    "cantidad": cantidad,
                    "costo_unitario": costo,
                }
            )

        ya_hay_ingreso = (
            db.execute(
                select(Abastecimiento)
                .where(Abastecimiento.proveedor_id == proveedor.id)
                .limit(1)
            )
            .scalar_one_or_none()
            is not None
        )
        if not ya_hay_ingreso:
            abastecimiento = servicio_abastecimientos.confirmar(
                db,
                {
                    "proveedor_id": proveedor.id,
                    "almacen_id": almacen.id,
                    "fecha": date.today() - timedelta(days=1),
                    "documento": "F001-00045",
                    "lineas": lineas,
                },
                usuario_id,
            )
            print(f"✔ Abastecimiento confirmado: {abastecimiento.numero}")

            # --- Ventas de ejemplo -----------------------------------------
            arroz = productos["AJO-001"]
            arroz_kg = next(p for p in arroz.presentaciones if p.nombre == "1 kg")
            gaseosa = productos["GAS-500"]
            gaseosa_paquete = next(p for p in gaseosa.presentaciones if p.nombre == "paquete x6")
            leche = productos["LEC-400"]
            leche_unidad = next(p for p in leche.presentaciones if p.nombre == "unidad")

            venta_1 = servicio_ventas.confirmar(
                db,
                {
                    "almacen_id": almacen.id,
                    "lineas": [
                        {
                            "producto_id": arroz.id,
                            "presentacion_id": arroz_kg.id,
                            "cantidad": "0.750",
                        },
                        {
                            "producto_id": leche.id,
                            "presentacion_id": leche_unidad.id,
                            "cantidad": "2",
                        },
                    ],
                },
                usuario_id,
            )
            print(f"✔ Venta de ejemplo: {venta_1.numero} (venta fraccionada)")

            venta_2 = servicio_ventas.confirmar(
                db,
                {
                    "almacen_id": almacen.id,
                    "lineas": [
                        {
                            "producto_id": gaseosa.id,
                            "presentacion_id": gaseosa_paquete.id,
                            "cantidad": "1",
                        }
                    ],
                },
                usuario_id,
            )
            print(f"✔ Venta de ejemplo: {venta_2.numero} (venta por paquete)")

        db.commit()
        print("✔ Datos de ejemplo cargados.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    cargar()


if __name__ == "__main__":
    sys.exit(main())
