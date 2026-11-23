"""Comprobación de la regla «1/2 saco» sobre la base de trabajo (solo lectura).

Verifica que:
- un producto con «1/2 saco = si» acepta vender 0,5 saco;
- un producto con «1/2 saco = no» rechaza la venta fraccionada;
- dos medios sacos consumen exactamente un saco del lote.

Uso:  python -m app.cli.verificar_medio_saco
"""

from __future__ import annotations

import sys
from decimal import Decimal

from sqlalchemy import select

from app.db.models import Almacen, Producto
from app.db.session import SessionLocal
from app.domain.unidades import ErrorNegocio
from app.services import ventas as servicio_ventas


def _producto(db, codigo: str) -> tuple[Producto, object]:
    producto = db.execute(
        select(Producto).where(Producto.codigo == codigo)
    ).scalar_one()
    presentacion = producto.presentaciones[0]
    return producto, presentacion


def main() -> int:
    db = SessionLocal()
    try:
        almacen = db.execute(
            select(Almacen).where(Almacen.activo.is_(True)).order_by(Almacen.id)
        ).scalars().first()

        # --- 1. Producto con «1/2 saco = si» (INV-001 AVES CRECIMIENTO) ------
        producto, presentacion = _producto(db, "INV-001")
        print(f"[1] {producto.codigo} {producto.nombre}")
        print(f"    permite_fraccion del producto: {producto.permite_fraccion}")
        print(f"    permite_fraccion de la presentacion: {presentacion.permite_fraccion}")
        try:
            previa = servicio_ventas.previsualizar(
                db,
                {
                    "almacen_id": almacen.id,
                    "lineas": [
                        {
                            "producto_id": producto.id,
                            "presentacion_id": presentacion.id,
                            "cantidad": "0.5",
                        }
                    ],
                },
            )
            linea = previa["lineas"][0]
            print(f"    medio saco ACCEPTADO -> cantidad_base={linea['cantidad_base']}")
        except ErrorNegocio as error:
            print(f"    ERROR: no deberia rechazar el medio saco -> {error}")
            return 1

        # --- 2. Producto con «1/2 saco = no» (INV-003 AVES INICIO) -----------
        producto_no, presentacion_no = _producto(db, "INV-003")
        print(f"[2] {producto_no.codigo} {producto_no.nombre}")
        print(f"    permite_fraccion del producto: {producto_no.permite_fraccion}")
        print(f"    permite_fraccion de la presentacion: {presentacion_no.permite_fraccion}")
        try:
            servicio_ventas.previsualizar(
                db,
                {
                    "almacen_id": almacen.id,
                    "lineas": [
                        {
                            "producto_id": producto_no.id,
                            "presentacion_id": presentacion_no.id,
                            "cantidad": "0.5",
                        }
                    ],
                },
            )
            print("    ERROR: deberia rechazar la venta fraccionada")
            return 1
        except ErrorNegocio as error:
            print(f"    fraccion RECHAZADA correctamente -> {error}")

        # --- 3. Saco entero aceptado en un producto «no» -------------------
        previa = servicio_ventas.previsualizar(
            db,
            {
                "almacen_id": almacen.id,
                "lineas": [
                    {
                        "producto_id": producto_no.id,
                        "presentacion_id": presentacion_no.id,
                        "cantidad": "1",
                    }
                ],
            },
        )
        print(
            f"[3] saco entero ACEPTADO -> cantidad_base={previa['lineas'][0]['cantidad_base']}"
        )

        # --- 4. El stock del lote, en sacos y medios sacos -------------------
        from app.services import lotes as servicio_lotes

        for codigo in ("INV-001", "VMP-001", "7271"):
            prod, _ = _producto(db, codigo)
            for lote in servicio_lotes.listar_lotes(db, prod.id):
                disponible = Decimal(lote["cantidad_disponible"])
                factor = Decimal(lote["factor_base"])
                print(
                    f"[4] {lote['codigo_lote']}: {disponible} g = "
                    f"{disponible / factor} x {lote['presentacion_nombre']}"
                )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
