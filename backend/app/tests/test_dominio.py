"""Pruebas unitarias de conversiones y costos (plan §6.1, §6.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.costing import costo_promedio_tras_entrada, costo_promedio_tras_salida
from app.domain.unidades import ErrorValidacionUnidad, convertir_a_base


def test_caja_de_24_unidades():
    conversion = convertir_a_base(
        Decimal("5"), Decimal("24"), 1, permite_fraccion=False
    )
    assert conversion.cantidad_base == Decimal("120")


def test_saco_de_50_kg_en_gramos():
    conversion = convertir_a_base(
        Decimal("3"), Decimal("50000"), 1, permite_fraccion=False
    )
    assert conversion.cantidad_base == Decimal("150000")


def test_venta_fraccionada_en_kilos():
    conversion = convertir_a_base(
        Decimal("0.750"), Decimal("1000"), 1, permite_fraccion=True
    )
    assert conversion.cantidad_base == Decimal("750")


def test_presentacion_indivisible_rechaza_fraccion():
    with pytest.raises(ErrorValidacionUnidad):
        convertir_a_base(Decimal("0.5"), Decimal("1"), 1, permite_fraccion=False)


def test_cantidad_no_positiva_rechazada():
    with pytest.raises(Exception):
        convertir_a_base(Decimal("0"), Decimal("1"), 1, permite_fraccion=True)


def test_costo_promedio_tras_entrada():
    # 100 unidades a 2.00 + 100 unidades a 4.00 => 3.00
    costo = costo_promedio_tras_entrada(
        Decimal("100"), Decimal("2"), Decimal("100"), Decimal("4")
    )
    assert costo == Decimal("3.000000")


def test_costo_promedio_con_stock_previo_cero():
    costo = costo_promedio_tras_entrada(
        Decimal("0"), Decimal("0"), Decimal("50"), Decimal("7.5")
    )
    assert costo == Decimal("7.500000")


def test_costo_promedio_tras_salida_conserva_valor():
    # 200 unidades a 3.00, se venden 50 a 3.00 => quedan 150 a 3.00
    costo = costo_promedio_tras_salida(
        Decimal("200"), Decimal("3"), Decimal("50"), Decimal("3")
    )
    assert costo == Decimal("3.000000")


def test_costo_promedio_tras_salida_total():
    costo = costo_promedio_tras_salida(
        Decimal("10"), Decimal("3"), Decimal("10"), Decimal("3")
    )
    assert costo == Decimal("0")


# --- Precios variables de la caja -------------------------------------------
def test_precio_sin_cambio_permite_el_precio_de_lista():
    from app.domain.precios import evaluar_precio

    resultado = evaluar_precio(
        "10.00", None, puede_editar_precio=True, puede_administrar_precios=False
    )
    assert resultado.permitido is True
    assert resultado.precio_aplicado == Decimal("10.00")
    assert resultado.hay_cambio is False


def test_descuento_dentro_del_limite_se_permite():
    from app.domain.precios import evaluar_precio

    resultado = evaluar_precio(
        "10.00",
        "8.00",
        puede_editar_precio=True,
        puede_administrar_precios=False,
        limite_porcentaje="20",
    )
    assert resultado.permitido is True
    assert resultado.precio_aplicado == Decimal("8.00")
    assert resultado.precio_original == Decimal("10.00")
    assert resultado.descuento_porcentaje == Decimal("20.0000")


def test_descuento_fuera_del_limite_se_rechaza():
    from app.domain.precios import evaluar_precio

    resultado = evaluar_precio(
        "10.00",
        "5.00",
        puede_editar_precio=True,
        puede_administrar_precios=False,
        limite_porcentaje="20",
    )
    assert resultado.permitido is False
    assert "límite" in (resultado.motivo or "")


def test_el_administrador_puede_superar_el_limite():
    from app.domain.precios import evaluar_precio

    resultado = evaluar_precio(
        "10.00",
        "5.00",
        puede_editar_precio=True,
        puede_administrar_precios=True,
        limite_porcentaje="20",
    )
    assert resultado.permitido is True
    assert resultado.precio_aplicado == Decimal("5.00")


def test_quien_no_puede_editar_mantiene_el_precio_de_lista():
    from app.domain.precios import evaluar_precio

    resultado = evaluar_precio(
        "10.00",
        "5.00",
        puede_editar_precio=False,
        puede_administrar_precios=False,
        limite_porcentaje="20",
    )
    assert resultado.permitido is True
    assert resultado.precio_aplicado == Decimal("10.00")


def test_subir_el_precio_requiere_administrador():
    from app.domain.precios import evaluar_precio

    vendedor = evaluar_precio(
        "10.00",
        "12.00",
        puede_editar_precio=True,
        puede_administrar_precios=False,
        limite_porcentaje="20",
    )
    assert vendedor.permitido is False

    administrador = evaluar_precio(
        "10.00",
        "12.00",
        puede_editar_precio=True,
        puede_administrar_precios=True,
        limite_porcentaje="20",
    )
    assert administrador.permitido is True
    assert administrador.precio_aplicado == Decimal("12.00")
