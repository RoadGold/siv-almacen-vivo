"""Pruebas de la limpieza de la base (empezar de cero con el catálogo).

La limpieza tiene que dejar la base como si el negocio acabara de instalar el
sistema: sin ventas, sin ingresos, sin stock y **solo con el catálogo de
balanceados**.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.cli.limpiar_operacion import MARCAS_CATALOGO


def _conteo(db, tabla: str) -> int:
    return db.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar_one()


@pytest.fixture
def base_con_datos(db, unidades, almacen):
    """Una base con operación y con productos de ejemplo, como la de trabajo."""
    from app.core.security import hash_password
    from app.db.models import Producto, PresentacionProducto, Usuario

    # Un producto de ejemplo (marca «Genérica») con su presentación.
    marca_id = db.execute(
        text("SELECT id FROM marcas WHERE nombre = 'Genérica'")
    ).scalar_one_or_none()
    if marca_id is None:
        from app.db.models import Marca

        marca = Marca(nombre="Genérica")
        db.add(marca)
        db.flush()
        marca_id = marca.id

    producto = Producto(
        codigo="LIM-001",
        nombre="Producto de ejemplo",
        nombre_normalizado="producto de ejemplo",
        unidad_base_id=unidades["UND"].id,
        marca_id=marca_id,
        stock_minimo_base=0,
        permite_fraccion=False,
        activo=True,
    )
    db.add(producto)
    db.flush()
    producto.presentaciones.append(
        PresentacionProducto(
            nombre="botella",
            factor_base=1,
            precio_venta=2,
            costo_referencia=1,
            es_compra=True,
            es_venta=True,
            permite_fraccion=False,
            activo=True,
        )
    )
    db.flush()
    db.commit()
    return producto


class TestLimpieza:
    """La limpieza deja la base como recién instalada, con el catálogo."""

    def test_borra_la_operacion(self, db, unidades, almacen, admin, base_con_datos):
        """Ventas, ingresos, movimientos, lotes y auditoría se vacían."""
        from app.cli.limpiar_operacion import limpiar

        # Se simula una venta para que haya operación que borrar.
        from app.db.models import Venta

        db.add(
            Venta(
                numero="V-TEST",
                almacen_id=almacen.id,
                fecha=almacen.created_at.date(),
                estado="CONFIRMADO",
                total=0,
                costo_total=0,
                usuario_id=admin.id,
            )
        )
        db.commit()

        limpiar(db.connection())

        for tabla in (
            "ventas",
            "abastecimientos",
            "movimientos_inventario",
            "existencias",
            "lotes_inventario",
            "auditoria",
            "ajustes_inventario",
        ):
            assert _conteo(db, tabla) == 0, f"la tabla {tabla} no quedó vacía"

    def test_borra_lo_que_no_es_del_catalogo(self, db, unidades, almacen, base_con_datos):
        """Los productos de ejemplo se van; los de balanceados se quedan."""
        from app.cli.limpiar_operacion import limpiar

        limpiar(db.connection())

        assert db.execute(
            text("SELECT COUNT(*) FROM productos WHERE codigo = 'LIM-001'")
        ).scalar_one() == 0

        # Los de balanceados siguen ahí.
        from app.cli.datos_balanceados_cargar import cargar

        cargar(db)
        balanceados = db.execute(
            text(
                "SELECT COUNT(*) FROM productos p "
                "JOIN marcas m ON m.id = p.marca_id "
                "WHERE m.nombre IN ('Vitamaxpro', 'Invita', 'Tomasino')"
            )
        ).scalar_one()
        assert balanceados == 143

    def test_conserva_los_datos_de_uso(self, db, unidades, almacen, base_con_datos):
        """Usuarios, roles, almacén y unidades se conservan: sin ellos no se entra."""
        from app.cli.limpiar_operacion import limpiar

        antes_usuarios = _conteo(db, "usuarios")
        antes_unidades = _conteo(db, "unidades_medida")
        antes_almacenes = _conteo(db, "almacenes")

        limpiar(db.connection())

        assert _conteo(db, "usuarios") == antes_usuarios
        assert _conteo(db, "unidades_medida") == antes_unidades
        assert _conteo(db, "almacenes") == antes_almacenes

    def test_reconstruye_los_vinculos_con_el_proveedor(self, db, unidades, almacen):
        """Después de limpiar, los vínculos se vuelven a crear al cargar."""
        from app.cli.datos_balanceados_cargar import cargar
        from app.cli.limpiar_operacion import limpiar

        cargar(db)
        limpiar(db.connection())
        assert _conteo(db, "productos_proveedores") == 0

        cargar(db)
        assert _conteo(db, "productos_proveedores") == 143

    def test_las_marcas_del_catalogo_son_las_esperadas(self):
        assert set(MARCAS_CATALOGO) == {"Vitamaxpro", "Invita", "Tomasino"}
