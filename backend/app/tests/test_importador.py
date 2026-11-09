"""Pruebas del importador de catálogo y de la carga de inventario inicial."""

from __future__ import annotations

import io

from openpyxl import Workbook


def _archivo_excel(filas: list[list]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.append(
        [
            "Código",
            "Nombre del producto",
            "Categoría",
            "Marca",
            "Unidad base (UND/GR/ML)",
            "Stock mínimo (unidad base)",
            "Presentación de venta",
            "Factor de conversión",
            "Precio de venta",
            "Costo de referencia",
            "Código de barras",
            "¿Admite fracción? (SI/NO)",
            "Stock inicial (opcional)",
            "Costo unitario inicial (opcional)",
        ]
    )
    for fila in filas:
        hoja.append(fila)
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def test_t18_importacion_con_vista_previa_y_sin_altas_silenciosas(
    cliente, cabeceras_admin, unidades, almacen
):
    contenido = _archivo_excel(
        [
            [
                "IMP-001",
                "Arroz a granel",
                "Granos",
                "Genérica",
                "GR",
                "10000",
                "1 kg",
                "1000",
                "5.00",
                "3.40",
                "",
                "SI",
                "50000",
                "0.0034",
            ],
            [
                "IMP-002",
                "Producto inválido",
                "Granos",
                "Genérica",
                "XXX",  # unidad inexistente
                "0",
                "unidad",
                "1",
                "1.00",
                "",
                "",
                "NO",
                "",
                "",
            ],
        ]
    )

    vista_previa = cliente.post(
        "/api/v1/catalogo/importar/previsualizar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    )
    assert vista_previa.status_code == 200, vista_previa.text
    cuerpo = vista_previa.json()
    assert cuerpo["resumen"]["filas"] == 2
    assert cuerpo["resumen"]["nuevos"] == 1
    assert cuerpo["resumen"]["con_errores"] == 1

    # Nada se creó todavía.
    assert (
        cliente.get(
            "/api/v1/catalogo/productos", params={"q": "IMP-001"}, headers=cabeceras_admin
        ).json()["total"]
        == 0
    )

    resultado = cliente.post(
        "/api/v1/catalogo/importar/confirmar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        params={"aplicar_stock_inicial": "true", "almacen_id": almacen.id},
        headers=cabeceras_admin,
    )
    assert resultado.status_code == 200, resultado.text
    cuerpo = resultado.json()
    assert cuerpo["importadas"] == 1
    assert cuerpo["rechazadas"] == 1
    assert cuerpo["productos_creados"] == 1

    # El stock inicial quedó cargado como SALDO_INICIAL.
    productos = cliente.get(
        "/api/v1/catalogo/productos", params={"q": "IMP-001"}, headers=cabeceras_admin
    ).json()
    assert productos["total"] == 1
    producto_id = productos["items"][0]["id"]

    existencias = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": almacen.id, "q": "IMP-001"},
        headers=cabeceras_admin,
    ).json()
    assert existencias["total"] == 1
    assert existencias["items"][0]["cantidad_base"] == "50000"

    movimientos = cliente.get(
        "/api/v1/inventario/movimientos",
        params={"producto_id": producto_id},
        headers=cabeceras_admin,
    ).json()
    assert movimientos["items"][0]["tipo"] == "SALDO_INICIAL"


def test_plantilla_excel_se_descarga(cliente, cabeceras_admin):
    respuesta = cliente.get("/api/v1/catalogo/importar/plantilla", headers=cabeceras_admin)
    assert respuesta.status_code == 200
    assert "spreadsheetml" in respuesta.headers["content-type"]


def test_carga_inventario_inicial_por_api(cliente, cabeceras_admin, unidades, almacen):
    producto = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "INIC-001",
            "nombre": "Producto inicial",
            "unidad_base_id": unidades["UND"].id,
            "presentaciones": [{"nombre": "unidad", "factor_base": "1", "precio_venta": "1.00"}],
        },
        headers=cabeceras_admin,
    ).json()

    respuesta = cliente.post(
        "/api/v1/inventario/inventario-inicial",
        json={
            "almacen_id": almacen.id,
            "referencia": "Conteo de apertura",
            "lineas": [
                {"producto_id": producto["id"], "cantidad_base": "120", "costo_unitario_base": "2.50"}
            ],
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["total_unidades_base"] == "120"

    # Una segunda carga del mismo producto se rechaza (ya tiene existencias).
    repetida = cliente.post(
        "/api/v1/inventario/inventario-inicial",
        json={
            "almacen_id": almacen.id,
            "lineas": [{"producto_id": producto["id"], "cantidad_base": "10"}],
        },
        headers=cabeceras_admin,
    )
    assert repetida.status_code == 400
