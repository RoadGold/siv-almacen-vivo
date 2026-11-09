"""Pruebas de reportes e indicadores (plan §5.7)."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.tests.test_flujo_completo import (
    abbreviaturas_presentaciones,
    crear_producto,
    crear_proveedor,
    ingresar,
)


def _preparar(cliente, cabeceras, unidades, almacen):
    arroz = crear_producto(
        cliente,
        cabeceras,
        unidades,
        codigo="REP-ARROZ",
        nombre="Arroz a granel",
        unidad="GR",
    )
    gaseosa = crear_producto(
        cliente,
        cabeceras,
        unidades,
        codigo="REP-GAS",
        nombre="Gaseosa 500 ml",
        unidad="UND",
        presentaciones=[
            {"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"},
            {"nombre": "caja x24", "factor_base": "24", "precio_venta": "48.00"},
        ],
    )
    ids_arroz = abbreviaturas_presentaciones(arroz)
    ids_gas = abbreviaturas_presentaciones(gaseosa)
    proveedor = crear_proveedor(cliente, cabeceras, "REP-PRV")
    ingresar(
        cliente,
        cabeceras,
        proveedor["id"],
        almacen.id,
        [
            {
                "producto_id": arroz["id"],
                "presentacion_id": ids_arroz["saco 50 kg"],
                "cantidad": "2",
                "costo_unitario": "170.00",
            },
            {
                "producto_id": gaseosa["id"],
                "presentacion_id": ids_gas["caja x24"],
                "cantidad": "3",
                "costo_unitario": "45.00",
            },
        ],
    )
    cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": gaseosa["id"],
                    "presentacion_id": ids_gas["botella"],
                    "cantidad": "4",
                }
            ],
        },
        headers=cabeceras,
    )
    return arroz, gaseosa, proveedor


def test_reporte_ventas_por_periodo_producto_y_usuario(
    cliente, cabeceras_admin, unidades, almacen
):
    _preparar(cliente, cabeceras_admin, unidades, almacen)

    reporte = cliente.get("/api/v1/reportes/ventas", headers=cabeceras_admin)
    assert reporte.status_code == 200, reporte.text
    cuerpo = reporte.json()

    periodo = cuerpo["periodo"]
    assert periodo["operaciones"] == 1
    assert periodo["total"] == "10"  # 4 botellas x 2.50
    # Costo de mercadería vendida: 4 unidades a 1.875 (costo promedio de la caja)
    assert periodo["costo"] == "7.5"
    assert periodo["margen_bruto_estimado"] == "2.5"

    productos = cuerpo["por_producto"]
    assert productos[0]["codigo"] == "REP-GAS"
    assert productos[0]["total"] == "10"

    categorias = cuerpo["por_categoria"]
    assert sum(c["total"] == "10" for c in categorias)

    usuarios = cuerpo["por_usuario"]
    assert usuarios[0]["usuario"] == "Administrador"


def test_reporte_margen_bruto_esta_etiquetado(
    cliente, cabeceras_admin, unidades, almacen
):
    _preparar(cliente, cabeceras_admin, unidades, almacen)
    margen = cliente.get("/api/v1/reportes/margen", headers=cabeceras_admin).json()
    assert "margen_bruto_estimado" in margen
    assert "No es utilidad neta" in margen["nota"]
    assert margen["ventas"] == "10"


def test_reporte_inventario_valorizado(cliente, cabeceras_admin, unidades, almacen):
    _preparar(cliente, cabeceras_admin, unidades, almacen)
    inventario = cliente.get("/api/v1/reportes/inventario", headers=cabeceras_admin).json()
    codigos = {i["codigo"] for i in inventario}
    assert {"REP-ARROZ", "REP-GAS"} <= codigos
    gaseosa = next(i for i in inventario if i["codigo"] == "REP-GAS")
    # 72 unidades x 1.875 = 135.00
    assert gaseosa["cantidad_base"] == "68"
    assert gaseosa["valor_costo"] == "127.5"


def test_historico_de_costos_por_proveedor(cliente, cabeceras_admin, unidades, almacen):
    _preparar(cliente, cabeceras_admin, unidades, almacen)
    costos = cliente.get("/api/v1/reportes/costos", headers=cabeceras_admin).json()
    assert len(costos) == 2
    assert costos[0]["proveedor"] == "Mayorista Central SAC"
    assert "costo_unitario" in costos[0]


def test_exportacion_csv_de_ventas(cliente, cabeceras_admin, unidades, almacen):
    _preparar(cliente, cabeceras_admin, unidades, almacen)
    respuesta = cliente.get("/api/v1/reportes/ventas/exportar", headers=cabeceras_admin)
    assert respuesta.status_code == 200
    assert "text/csv" in respuesta.headers["content-type"]
    contenido = respuesta.content.decode("utf-8")
    assert contenido.startswith("\ufeff")  # BOM para Excel
    assert "Numero" in contenido
    assert "REP-GAS" in contenido
