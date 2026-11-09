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
