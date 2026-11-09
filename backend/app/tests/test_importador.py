"""Pruebas del importador de catálogo y de la carga de inventario inicial."""

from __future__ import annotations

import io

from openpyxl import Workbook
from sqlalchemy import select


def _plantilla(filas: list[list]) -> bytes:
    """Arma un archivo con los encabezados de la plantilla real del sistema."""
    from app.services import importador

    libro = Workbook()
    hoja = libro.active
    hoja.append([importador.TITULOS[columna] for columna in importador.COLUMNAS])
    for fila in filas:
        hoja.append(fila)
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


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
            "Código del proveedor (opcional)",
            "¿Proveedor habitual? (SI/NO)",
            "Presentación de compra (opcional)",
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


# --- Carga inicial: reglas de seguridad --------------------------------------
def test_stock_inicial_se_aplica_una_sola_vez_por_producto(
    cliente, cabeceras_admin, unidades, almacen
):
    """Un producto con varias presentaciones recibe el stock inicial una vez."""
    contenido = _plantilla(
        [
            ["P900", "Producto de prueba", "Abarrotes", "Genérica", "UND", "0", "botella", "1", "2.50", "1.90", "", "NO", "10", "1.90"],
            ["P900", "Producto de prueba", "Abarrotes", "Genérica", "UND", "0", "caja x24", "24", "48.00", "45.60", "", "NO", "10", "1.90"],
        ]
    )
    resultado = cliente.post(
        "/api/v1/catalogo/importar/confirmar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        params={"aplicar_stock_inicial": "true", "almacen_id": almacen.id},
        headers=cabeceras_admin,
    )
    assert resultado.status_code == 200, resultado.text
    cuerpo = resultado.json()
    assert cuerpo["stock_inicial_aplicado"] == 1

    existencias = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": almacen.id, "q": "P900"},
        headers=cabeceras_admin,
    ).json()
    assert existencias["total"] == 1
    assert existencias["items"][0]["cantidad_base"] == "10"


def test_reimportar_no_vuelve_a_sumar_el_stock(cliente, cabeceras_admin, unidades, almacen):
    """Subir dos veces el mismo archivo no duplica las existencias."""
    contenido = _plantilla(
        [["P901", "Producto idempotente", "Abarrotes", "Genérica", "UND", "0", "unidad", "1", "2.50", "1.90", "", "NO", "25", "1.90"]]
    )
    archivos = {"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    primera = cliente.post(
        "/api/v1/catalogo/importar/confirmar",
        files=archivos,
        params={"aplicar_stock_inicial": "true", "almacen_id": almacen.id},
        headers=cabeceras_admin,
    ).json()
    assert primera["stock_inicial_aplicado"] == 1

    segunda = cliente.post(
        "/api/v1/catalogo/importar/confirmar",
        files=archivos,
        params={"aplicar_stock_inicial": "true", "almacen_id": almacen.id},
        headers=cabeceras_admin,
    ).json()
    assert segunda["stock_inicial_aplicado"] == 0

    existencias = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": almacen.id, "q": "P901"},
        headers=cabeceras_admin,
    ).json()
    assert existencias["items"][0]["cantidad_base"] == "25"


def test_vista_previa_avisa_del_stock_repetido_y_del_stock_ya_cargado(
    cliente, cabeceras_admin, unidades, almacen
):
    contenido = _plantilla(
        [
            ["P902", "Producto con aviso", "Abarrotes", "Genérica", "UND", "0", "unidad", "1", "2.50", "1.90", "", "NO", "10", "1.90"],
            ["P902", "Producto con aviso", "Abarrotes", "Genérica", "UND", "0", "caja x24", "24", "48.00", "45.60", "", "NO", "10", "1.90"],
        ]
    )
    previa = cliente.post(
        "/api/v1/catalogo/importar/previsualizar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    ).json()
    avisos = " ".join(aviso for fila in previa["filas"] for aviso in fila["avisos"])
    assert "una sola vez" in avisos
    assert previa["resumen"]["con_avisos"] >= 1
    assert previa["resumen"]["con_stock_inicial"] == 1


# --- Proveedor dentro de la importación -------------------------------------
def test_la_importacion_vincula_el_proveedor(cliente, cabeceras_admin, unidades, almacen):
    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-IMP", "razon_social": "Distribuidora Importada SAC"},
        headers=cabeceras_admin,
    ).json()

    contenido = _plantilla(
        [["P903", "Producto con proveedor", "Abarrotes", "Genérica", "UND", "0", "unidad", "1", "2.50", "1.90", "", "NO", "", "", "PRV-IMP", "SI", "unidad"]]
    )
    resultado = cliente.post(
        "/api/v1/catalogo/importar/confirmar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    )
    assert resultado.status_code == 200, resultado.text
    cuerpo = resultado.json()
    assert cuerpo["vinculos_proveedor"] == 1

    productos = cliente.get(
        "/api/v1/proveedores/{}/productos".format(proveedor["id"]), headers=cabeceras_admin
    ).json()
    assert len(productos) == 1
    assert productos[0]["codigo"] == "P903"
    assert productos[0]["habitual"] is True


def test_proveedor_desconocido_marca_la_fila_con_error(cliente, cabeceras_admin, unidades):
    contenido = _plantilla(
        [["P904", "Producto sin proveedor valido", "Abarrotes", "Genérica", "UND", "0", "unidad", "1", "2.50", "1.90", "", "NO", "", "", "PRV-NO-EXISTE", "SI", ""]]
    )
    previa = cliente.post(
        "/api/v1/catalogo/importar/previsualizar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    ).json()
    assert previa["resumen"]["con_errores"] == 1
    assert "no está registrado" in previa["filas"][0]["mensajes"][0]


def test_producto_sin_proveedor_se_importa_sin_problemas(cliente, cabeceras_admin, unidades, almacen):
    """El escenario del cliente: productos que aún no tienen proveedor conocido."""
    contenido = _plantilla(
        [["P905", "Producto sin proveedor", "Abarrotes", "Genérica", "UND", "0", "unidad", "1", "2.50", "1.90", "", "NO", "12", "1.90", "", "", ""]]
    )
    previa = cliente.post(
        "/api/v1/catalogo/importar/previsualizar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    ).json()
    assert previa["resumen"]["con_errores"] == 0

    resultado = cliente.post(
        "/api/v1/catalogo/importar/confirmar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        params={"aplicar_stock_inicial": "true", "almacen_id": almacen.id},
        headers=cabeceras_admin,
    ).json()
    assert resultado["importadas"] == 1
    assert resultado["stock_inicial_aplicado"] == 1


def test_avisa_de_posibles_duplicados_por_nombre(cliente, cabeceras_admin, unidades):
    cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "P906",
            "nombre": "Arroz a granel",
            "unidad_base_id": unidades["GR"].id,
            "presentaciones": [{"nombre": "1 kg", "factor_base": "1000"}],
        },
        headers=cabeceras_admin,
    )
    contenido = _plantilla(
        [["P907", "Arroz a granel", "Abarrotes", "Genérica", "GR", "0", "1 kg", "1000", "5.00", "3.40", "", "SI", "", "", "", "", ""]]
    )
    previa = cliente.post(
        "/api/v1/catalogo/importar/previsualizar",
        files={"archivo": ("catalogo.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    ).json()
    avisos = " ".join(aviso for fila in previa["filas"] for aviso in fila["avisos"])
    assert "mismo nombre" in avisos or "Ya existe un producto con el nombre" in avisos
