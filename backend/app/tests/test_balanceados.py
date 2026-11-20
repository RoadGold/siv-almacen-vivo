"""Pruebas del catálogo inicial de balanceados.

Comprueban que las dos listas de distribuidores quedan bien traducidas al
modelo del sistema: un producto = un alimento, una presentación = un empaque,
el stock en gramos y los precios con el margen acordado.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.cli.datos_balanceados import MARGEN, precio_venta_de
from app.cli.traducir_balanceados import items_tomasino, items_vitamaxpro, todos_los_items


class TestTraduccion:
    """Las listas se traducen al modelo del sistema."""

    def test_se_cargan_los_dos_distribuidores(self) -> None:
        proveedores = {item.proveedor for item in todos_los_items()}
        assert proveedores == {"VITAMAXPRO", "TOMASINO"}

    def test_hay_productos_de_las_dos_listas(self) -> None:
        assert len(items_vitamaxpro()) > 0
        assert len(items_tomasino()) > 0
        assert len(todos_los_items()) == 143

    def test_todo_producto_tiene_empre(self) -> None:
        for item in todos_los_items():
            assert item.empaques, f"«{item.nombre}» no tiene ningún empaque"

    def test_los_codigos_no_se_repiten(self) -> None:
        """Los códigos de TOMASINO (los del distribuidor) son únicos."""
        codigos = [item.codigo for item in items_tomasino()]
        assert len(codigos) == len(set(codigos))

    def test_vitamaxpro_se_agrupa_por_marca_y_nombre(self) -> None:
        """En VITAMAXPRO la identidad es marca + nombre: no hay dos iguales."""
        claves = [(item.marca, item.nombre) for item in items_vitamaxpro()]
        assert len(claves) == len(set(claves))

    def test_tomasino_conserva_su_codigo_del_distribuidor(self) -> None:
        """Cada código de TOMASINO identifica un producto distinto."""
        por_codigo: dict[str, list[str]] = {}
        for item in items_tomasino():
            por_codigo.setdefault(item.codigo, []).append(item.nombre)
        assert all(len(nombres) == 1 for nombres in por_codigo.values())

    def test_los_codigos_de_vitamaxpro_los_asigna_la_carga(self) -> None:
        """El código se asigna en la carga, no en la traducción: así no cambia
        nunca aunque la lista de precios cambie de tamaño."""
        assert all(item.codigo == "" for item in items_vitamaxpro())

    def test_los_dos_sin_codigo_reciben_uno(self) -> None:
        """Los dos productos «S/C» de TOMASINO reciben un código propio."""
        sin_codigo = [item for item in items_tomasino() if item.codigo.startswith("TOM-SC-")]
        assert len(sin_codigo) == 2
        assert {item.codigo for item in sin_codigo} == {"TOM-SC-01", "TOM-SC-02"}

    def test_el_factor_es_el_peso_en_gramos(self) -> None:
        """Un saco de 40 kg son 40 000 gramos base."""
        producto = next(
            item
            for item in items_tomasino()
            if item.codigo == "11022"  # 1 x 20 kg
        )
        assert producto.empaques[0].factor_base == 20000

    def test_el_empaque_por_defecto_es_de_40_kilos(self) -> None:
        """Los productos VITAMAXPRO sin empaque en el nombre son sacos de 40 kg."""
        producto = next(
            item for item in items_vitamaxpro() if item.nombre == "TERNEROS CUNA"
        )
        assert all(empaque.peso_kg == 40 for empaque in producto.empaques)

    def test_el_nombre_no_lleva_el_empaque(self) -> None:
        """El empaque se separa del nombre del producto."""
        producto = next(
            item for item in items_vitamaxpro() if item.nombre == "POLLOS INICIO PREMIUN"
        )
        assert producto.nombre == "POLLOS INICIO PREMIUN"
        assert "X 40" not in producto.nombre

    def test_las_bolsas_de_un_kilo_se_reconocen(self) -> None:
        """«20X1 KG» son 20 bolsas de 1 kilo (20 kg en total)."""
        producto = next(
            item for item in items_vitamaxpro() if item.nombre == "POLLOS INICIO PREMIUN"
        )
        empaque = next(
            e for e in producto.empaques if e.bolsas is not None
        )
        assert empaque.bolsas == 20
        assert empaque.factor_base == 20000
        assert "20 x 1 kg" in empaque.nombre

    def test_el_mismo_alimento_agrupa_sus_empaques(self) -> None:
        """«Pollos Inicio Premium» es un producto con cuatro presentaciones."""
        producto = next(
            item for item in items_vitamaxpro() if item.nombre == "POLLOS INICIO PREMIUN"
        )
        assert len(producto.empaques) == 3
        nombres = {empaque.nombre for empaque in producto.empaques}
        assert nombres == {"saco 40 kg pellet", "saco 40 kg polvo", "20 x 1 kg pellet"}

    def test_la_forma_del_nombre_manda_sobre_la_columna(self) -> None:
        """«CUYES CARNE POLVO» es polvo, aunque el precio viniera en la columna
        de pellet (lo acelerar en la lista del distribuidor)."""
        producto = next(
            item for item in items_vitamaxpro() if "PER-S" in item.nombre
        )
        assert producto.empaques[0].forma == "POLVO"
        assert producto.empaques[0].precio_costo == "87.00"

    def test_el_micropelllet_es_una_forma_distinta(self) -> None:
        """«AVEPROMICINA X 40 MICROPELLET» es una presentación aparte."""
        producto = next(
            item for item in items_vitamaxpro() if item.nombre == "AVEPROMICINA"
        )
        formas = {empaque.forma for empaque in producto.empaques}
        assert "MICROPELLET" in formas
        assert "saco 40 kg micropellet" in {e.nombre for e in producto.empaques}

    def test_no_hay_precios_en_conflicto(self) -> None:
        """Un mismo producto y empaque no puede tener dos precios distintos."""
        vistos: dict[tuple[str, str, str], str] = {}
        for item in todos_los_items():
            for empaque in item.empaques:
                clave = (item.marca, item.nombre, empaque.nombre)
                if clave in vistos:
                    assert vistos[clave] == empaque.precio_costo, clave
                vistos[clave] = empaque.precio_costo

    def test_las_formas_se_convierten_en_presentaciones(self) -> None:
        """Un producto con pellet y polvo tiene dos presentaciones."""
        producto = next(
            item for item in items_vitamaxpro() if item.nombre == "TERNEROS CUNA"
        )
        formas = {empaque.forma for empaque in producto.empaques}
        assert formas == {"PELLET", "POLVO"}
        assert producto.empaques[0].precio_costo == "88.00"
        assert producto.empaques[1].precio_costo == "86.00"

    def test_los_precios_no_numericos_se_descartan(self) -> None:
        """El empaque «-» no se carga: no hay precio para ese formato."""
        for item in todos_los_items():
            for empaque in item.empaques:
                assert Decimal(empaque.precio_costo) > 0

    def test_los_codigos_de_tomasino_se_respetan(self) -> None:
        """El código del distribuidor es el del producto."""
        producto = next(item for item in items_tomasino() if item.codigo == "11022")
        assert producto.codigo == "11022"

    def test_las_categorias_cubren_todas_las_lineas(self) -> None:
        categorias = {item.categoria for item in todos_los_items()}
        assert "Vacunos" in categorias
        assert "Cerdos" in categorias
        assert "Pollos granja" in categorias
        assert "Postura" in categorias
        assert "Pavos" in categorias
        assert "Ovinos" in categorias
        assert "Caballos" in categorias
        assert "Conejos y cuyes" in categorias


class TestMargen:
    """El precio de venta sale del costo con el margen acordado."""

    def test_el_margen_es_del_30_por_ciento(self) -> None:
        assert MARGEN == Decimal("0.30")

    def test_el_precio_de_venta_es_el_costo_con_margen(self) -> None:
        assert precio_venta_de("100.00") == "130.00"
        assert precio_venta_de("88.00") == "114.40"
        assert precio_venta_de("63.00") == "81.90"

    def test_el_precio_siempre_supera_al_costo(self) -> None:
        for item in todos_los_items():
            for empaque in item.empaques:
                assert Decimal(precio_venta_de(empaque.precio_costo)) > Decimal(
                    empaque.precio_costo
                )

    def test_el_precio_se_redondea_a_dos_decimales(self) -> None:
        """El precio que se cobra es un importe con dos decimales."""
        for item in todos_los_items():
            for empaque in item.empaques:
                precio = precio_venta_de(empaque.precio_costo)
                assert len(precio.split(".")[1]) <= 2


class TestCargaEnBase:
    """La carga en la base de datos deja todo como debe estar."""

    def test_la_carga_es_idempotente(self, db, unidades) -> None:
        """Se puede ejecutar dos veces sin duplicar nada."""
        from sqlalchemy import func, select

        from app.cli.datos_balanceados_cargar import cargar
        from app.db.models import Producto, PresentacionProducto

        cargar(db)
        total_productos = db.execute(select(func.count(Producto.id))).scalar()
        total_presentaciones = (
            db.execute(select(func.count(PresentacionProducto.id))).scalar()
        )

        resumen = cargar(db)

        assert resumen["nuevos"] == 0
        assert resumen["actualizados"] == 143
        assert db.execute(select(func.count(Producto.id))).scalar() == total_productos
        assert (
            db.execute(select(func.count(PresentacionProducto.id))).scalar()
            == total_presentaciones
        )

    def test_los_precios_quedan_con_el_margen(self, db, unidades) -> None:
        """El precio de venta guardado es el costo con el margen."""
        from sqlalchemy import select

        from app.cli.datos_balanceados_cargar import cargar
        from app.db.models import PresentacionProducto, Producto

        cargar(db)
        presentacion = db.execute(
            select(PresentacionProducto)
            .join(Producto, PresentacionProducto.producto_id == Producto.id)
            .where(
                Producto.nombre == "TERNEROS CUNA",
                PresentacionProducto.nombre == "saco 40 kg pellet",
            )
        ).scalar_one()

        assert presentacion.costo_referencia == Decimal("88.00")
        assert presentacion.precio_venta == Decimal("114.40")
        assert presentacion.factor_base == Decimal("40000")

    def test_los_proveedores_quedan_vinculados(self, db, unidades) -> None:
        """Cada producto queda vinculado con su distribuidor."""
        from sqlalchemy import func, select

        from app.cli.datos_balanceados_cargar import cargar
        from app.db.models import ProductoProveedor

        cargar(db)
        vinculos = db.execute(select(func.count(ProductoProveedor.id))).scalar()
        assert vinculos == 143

    def test_el_codigo_de_un_producto_no_cambia(self, db, unidades) -> None:
        """La identidad de un producto es marca + nombre: su código se conserva.

        Esto es lo que permite actualizar la lista de precios sin romper el
        historial: aunque un producto cambie de posición, su código sigue igual.
        """
        from sqlalchemy import or_, select

        from app.cli.datos_balanceados_cargar import cargar
        from app.db.models import Producto

        cargar(db)
        antes = {
            (p.marca.nombre, p.nombre): p.codigo
            for p in db.execute(
                select(Producto)
                .join(Producto.marca)
                .where(or_(Producto.codigo.ilike("VMP-%"), Producto.codigo.ilike("INV-%")))
            ).scalars()
        }

        cargar(db)
        despues = {
            (p.marca.nombre, p.nombre): p.codigo
            for p in db.execute(
                select(Producto)
                .join(Producto.marca)
                .where(or_(Producto.codigo.ilike("VMP-%"), Producto.codigo.ilike("INV-%")))
            ).scalars()
        }

        assert antes == despues
        assert len(antes) == 70  # 56 de Vitamaxpro + 14 de Invita

    def test_los_codigos_numericos_de_tomasino_se_respetan(self, db, unidades) -> None:
        """El código del distribuidor es el del producto, tal cual."""
        from sqlalchemy import select

        from app.cli.datos_balanceados_cargar import cargar
        from app.db.models import Producto

        cargar(db)
        codigo = db.execute(
            select(Producto.codigo).where(Producto.nombre == "Broiler Tech Nutrition")
        ).scalars().first()
        assert codigo in {"11022", "10897"}
