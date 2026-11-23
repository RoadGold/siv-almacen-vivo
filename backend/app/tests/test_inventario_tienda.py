"""Pruebas de la carga del inventario físico de la tienda.

Comprueban:
- que el archivo de datos tenga las 128 líneas del inventario;
- que la carga cree productos, presentaciones, lotes y existencias;
- que la carga sea idempotente (se puede volver a ejecutar sin duplicar);
- que los duplicados del catálogo base queden fusionados y desactivados;
- que la regla «1/2 saco» se aplique al producto y a sus presentaciones.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.cli.cargar_inventario_tienda import (
    FUSIONES_DUPLICADOS,
    ITEMS_INVENTARIO_TIENDA,
    cargar_inventario_tienda,
)
from app.db.models import (
    Existencia,
    LoteInventario,
    LotePrecio,
    MovimientoInventario,
    PresentacionProducto,
    Producto,
)


@pytest.fixture
def base_preparada(db, unidades, almacen):
    """Catálogo de balanceados cargado (como en el equipo de trabajo)."""
    from app.cli.datos_balanceados_cargar import cargar

    cargar(db)
    db.commit()
    return {"almacen": almacen}


class TestDatosDelInventario:
    """El archivo de datos refleja el inventario de la tienda."""

    def test_tiene_las_128_lineas(self) -> None:
        assert len(ITEMS_INVENTARIO_TIENDA) == 128

    def test_los_codigos_de_producto_no_se_repiten_por_linea(self) -> None:
        """Un producto puede tener varias líneas (una por presentación), pero
        nunca dos líneas con la misma presentación."""
        pares = [(item.codigo, item.presentacion) for item in ITEMS_INVENTARIO_TIENDA]
        assert len(pares) == len(set(pares))

    def test_todas_las_cantidades_son_no_negativas(self) -> None:
        for item in ITEMS_INVENTARIO_TIENDA:
            assert Decimal(item.cantidad) >= 0, item.codigo

    def test_las_unidades_base_existen(self, unidades) -> None:
        for item in ITEMS_INVENTARIO_TIENDA:
            assert item.unidad_base in unidades, item.codigo

    def test_las_fusiones_apuntan_a_productos_existentes(self) -> None:
        assert len(FUSIONES_DUPLICADOS) == 9


class TestCargaDelInventario:
    """La carga deja el catálogo y el stock como el conteo físico."""

    def test_crea_los_lotes_y_las_existencias(self, db, base_preparada):
        almacen = base_preparada["almacen"]
        resumen = cargar_inventario_tienda(db)

        assert resumen["lineas_lista"] == 128
        assert resumen["fusiones"] == 9
        # 116 líneas con cantidad: un lote por línea.
        assert resumen["lotes_iniciales"] == 116
        assert resumen["lineas_sin_stock"] == 12

        lotes = db.execute(
            select(func.count()).select_from(LoteInventario)
        ).scalar_one()
        assert lotes == 116

        # La existencia consolidada es la suma de los lotes.
        for existencia in db.execute(select(Existencia)).scalars().all():
            suma = db.execute(
                select(func.coalesce(func.sum(LoteInventario.cantidad_disponible), 0)).where(
                    LoteInventario.producto_id == existencia.producto_id,
                    LoteInventario.almacen_id == existencia.almacen_id,
                )
            ).scalar_one()
            assert Decimal(str(existencia.cantidad_base)) == Decimal(str(suma))

    def test_el_stock_coincide_con_el_conteo(self, db, base_preparada):
        """137 sacos de AVES CRECIMIENTO = 137 x 40 000 g."""
        cargar_inventario_tienda(db)
        producto = db.execute(
            select(Producto).where(Producto.codigo == "INV-001")
        ).scalar_one()
        lote = db.execute(
            select(LoteInventario).where(LoteInventario.producto_id == producto.id)
        ).scalar_one()
        assert lote.cantidad_disponible == Decimal("5480000")
        assert lote.origen == "INVENTARIO_INICIAL"

    def test_es_idempotente(self, db, base_preparada):
        """Se puede volver a ejecutar la carga sin duplicar el stock."""
        cargar_inventario_tienda(db)
        antes = db.execute(select(func.count()).select_from(LoteInventario)).scalar_one()
        movimientos_antes = db.execute(
            select(func.count()).select_from(MovimientoInventario)
        ).scalar_one()

        cargar_inventario_tienda(db)

        assert db.execute(select(func.count()).select_from(LoteInventario)).scalar_one() == antes
        assert (
            db.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
            == movimientos_antes
        )

    def test_crea_los_productos_nuevos(self, db, base_preparada):
        """Los productos que no estaban en el catálogo base se crean."""
        cargar_inventario_tienda(db)
        total = db.execute(select(func.count()).select_from(Producto)).scalar_one()
        # 143 del catálogo base + los nuevos del inventario de la tienda.
        assert total >= 143 + 100

        for codigo in ("MED-001", "BOL-001", "MAS-001", "PRI-001", "SEQ-001", "VMP-057"):
            producto = db.execute(
                select(Producto).where(Producto.codigo == codigo)
            ).scalar_one()
            assert producto.activo is True
            assert producto.presentaciones


class TestDuplicados:
    """Los duplicados del catálogo base se fusionan y se desactivan."""

    def test_fusiona_las_presentaciones(self, db, base_preparada):
        cargar_inventario_tienda(db)

        avemed = db.execute(
            select(Producto).where(Producto.codigo == "7271")
        ).scalar_one()
        nombres = {p.nombre for p in avemed.presentaciones}
        assert "20 x 1 kg pellet" in nombres
        assert "saco 40 kg pellet" in nombres

    def test_desactiva_el_producto_duplicado(self, db, base_preparada):
        cargar_inventario_tienda(db)
        duplicado = db.execute(
            select(Producto).where(Producto.codigo == "9990")
        ).scalar_one()
        assert duplicado.activo is False
        for presentacion in duplicado.presentaciones:
            assert presentacion.activo is False

    def test_conserva_la_marca_invitada(self, db, base_preparada):
        """CERDOS ENGORDE y MARRANAS LACTANTES se quedan en la marca Invita."""
        cargar_inventario_tienda(db)
        conservado = db.execute(
            select(Producto).where(Producto.codigo == "INV-005")
        ).scalar_one()
        desactivado = db.execute(
            select(Producto).where(Producto.codigo == "VMP-006")
        ).scalar_one()
        assert conservado.activo is True
        assert desactivado.activo is False
        # La presentación exclusiva de Vitamaxpro pasa al producto conservado.
        assert any(p.nombre == "saco 50 kg polvo" for p in conservado.presentaciones)


class TestReglaMedioSaco:
    """La columna «1/2 saco» decide si el producto se vende en medios sacos."""

    def test_un_producto_con_medio_saco_admite_fraccion(self, db, base_preparada):
        cargar_inventario_tienda(db)
        producto = db.execute(
            select(Producto).where(Producto.codigo == "INV-001")
        ).scalar_one()
        assert producto.permite_fraccion is True
        for presentacion in producto.presentaciones:
            if presentacion.activo:
                assert presentacion.permite_fraccion is True

    def test_un_producto_solo_sacos_no_admite_fraccion(self, db, base_preparada):
        cargar_inventario_tienda(db)
        producto = db.execute(
            select(Producto).where(Producto.codigo == "INV-003")
        ).scalar_one()
        assert producto.permite_fraccion is False
        for presentacion in producto.presentaciones:
            if presentacion.activo:
                assert presentacion.permite_fraccion is False

    def test_los_lotes_conservan_el_precio_del_catalogo(self, db, base_preparada):
        """El lote inicial toma el costo de referencia y el precio de venta."""
        cargar_inventario_tienda(db)
        producto = db.execute(
            select(Producto).where(Producto.codigo == "INV-001")
        ).scalar_one()
        presentacion = producto.presentaciones[0]
        lote = db.execute(
            select(LoteInventario).where(LoteInventario.producto_id == producto.id)
        ).scalar_one()
        assert lote.precio_venta == presentacion.precio_venta
        assert lote.costo_base > 0
        # El precio del lote queda también en su tabla de precios por presentación.
        precio = db.execute(
            select(LotePrecio).where(LotePrecio.lote_id == lote.id)
        ).scalar_one()
        assert precio.precio == presentacion.precio_venta
