"""Pruebas de la limpieza de la base (empezar de cero).

Hay dos niveles:

- **limpiar la operación**: vacía ventas, ingresos, movimientos, lotes y
  auditoría, y **conserva todo el catálogo** (incluidos los productos que no
  son de balanceados).
- **reiniciar la base**: además del catálogo, lo borra todo, menos los
  usuarios, el almacén, las unidades y la configuración del negocio.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.cli.limpiar_operacion import (
    TABLAS_CATALOGO,
    TABLAS_OPERACION,
    limpiar,
    reiniciar,
)


def _conteo(db, tabla: str) -> int:
    return db.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar_one()


@pytest.fixture
def base_con_datos(db, unidades, almacen):
    """Una base con operación y con productos de ejemplo, como la de trabajo."""
    from app.db.models import Producto, PresentacionProducto

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
    """La limpieza deja la base sin operación y con el catálogo entero."""

    def test_borra_la_operacion(self, db, unidades, almacen, admin, base_con_datos):
        """Ventas, ingresos, movimientos, lotes y auditoría se vacían."""
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

    def test_conserva_todo_el_catalogo(self, db, unidades, almacen, base_con_datos):
        """La limpieza ya no borra productos: el catálogo se conserva entero."""
        limpiar(db.connection())

        assert db.execute(
            text("SELECT COUNT(*) FROM productos WHERE codigo = 'LIM-001'")
        ).scalar_one() == 1
        assert db.execute(text("SELECT COUNT(*) FROM presentaciones_producto")).scalar_one() >= 1

    def test_conserva_los_datos_de_uso(self, db, unidades, almacen, admin, base_con_datos):
        """Usuarios, roles, almacén, unidades y configuración se conservan."""
        antes_usuarios = _conteo(db, "usuarios")
        antes_unidades = _conteo(db, "unidades_medida")
        antes_almacenes = _conteo(db, "almacenes")
        antes_config = _conteo(db, "configuracion")

        limpiar(db.connection())

        assert _conteo(db, "usuarios") == antes_usuarios
        assert _conteo(db, "unidades_medida") == antes_unidades
        assert _conteo(db, "almacenes") == antes_almacenes
        assert _conteo(db, "configuracion") == antes_config

    def test_el_catalogo_y_sus_vinculos_se_conservan(self, db, unidades, almacen):
        """La limpieza de la operación no toca el catálogo ni sus vínculos."""
        from app.cli.datos_balanceados_cargar import cargar

        cargar(db)
        antes = _conteo(db, "productos_proveedores")
        assert antes == 143

        limpiar(db.connection())

        assert _conteo(db, "productos_proveedores") == antes
        assert _conteo(db, "productos") == 143

    def test_reinicia_las_secuencias(self, db, unidades, almacen, base_con_datos):
        """La primera venta vuelve a ser la V-000001."""
        from app.services import secuencias

        db.execute(
            text(
                "INSERT INTO secuencias (tipo, almacen_id, valor) "
                "VALUES ('VENTA', :almacen, 42) "
                "ON CONFLICT (tipo, almacen_id) DO UPDATE SET valor = 42"
            ),
            {"almacen": almacen.id},
        )
        db.commit()

        limpiar(db.connection())

        assert _conteo(db, "secuencias") == 0
        numero = secuencias.siguiente_numero(db, "VENTA", almacen.id)
        assert numero == "V-000001"


class TestReinicio:
    """El reinicio deja la base totalmente vacía."""

    def test_vacia_la_operacion_y_el_catalogo(
        self, db, unidades, almacen, admin, base_con_datos
    ):
        reiniciar(db.connection())

        for tabla in TABLAS_OPERACION + TABLAS_CATALOGO:
            assert _conteo(db, tabla) == 0, f"la tabla {tabla} no quedó vacía"

    def test_conserva_lo_esencial(self, db, unidades, almacen, admin, base_con_datos):
        """Usuarios, roles, almacén, unidades y configuración siguen ahí."""
        antes_usuarios = _conteo(db, "usuarios")
        antes_unidades = _conteo(db, "unidades_medida")
        antes_almacenes = _conteo(db, "almacenes")

        reiniciar(db.connection())

        assert _conteo(db, "usuarios") == antes_usuarios
        assert _conteo(db, "unidades_medida") == antes_unidades
        assert _conteo(db, "almacenes") == antes_almacenes

    def test_el_catalogo_se_puede_volver_a_cargar(self, db, unidades, almacen):
        """Tras el reinicio, el catálogo se carga otra vez sin problemas."""
        from app.cli.datos_balanceados_cargar import cargar

        reiniciar(db.connection())
        cargar(db)

        assert db.execute(text("SELECT COUNT(*) FROM productos")).scalar_one() == 143
        assert db.execute(text("SELECT COUNT(*) FROM proveedores")).scalar_one() == 2
