"""Pruebas de regresión de los agujeros de validación encontrados.

Cada prueba reproduce un caso que **antes** pasaba sin que nadie se enterara:
datos que se guardaban mal, se perdían o se aceptaban sin aviso. Están aquí
para que no vuelvan.

Los casos son:
- A · La venta en efectivo por debajo del total se perdía (no se veía lo que
      faltaba por cobrar).
- B · La forma de pago aceptaba cualquier texto.
- C · Editar un proveedor no limpiaba los campos vaciados, y el RUC repetido
      no se rechazaba al editar.
- D · La configuración del negocio aceptaba cualquier texto (un nombre de 500
      caracteres y un RUC «abc» iban al ticket).
- E · La importación de catálogo se saltaba las reglas del alta de producto
      (un stock mínimo negativo se guardaba).
"""

from __future__ import annotations

from fastapi.testclient import TestClient


# --- Utilidades de apoyo ---------------------------------------------------


def _crear_producto(cliente: TestClient, cabeceras: dict, unidades: dict) -> dict:
    respuesta = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "PRD-VAL",
            "nombre": "Producto de prueba",
            "unidad_base_id": unidades["UND"].id,
            "stock_minimo_base": "0",
            "permite_fraccion": False,
            "presentaciones": [
                {
                    "nombre": "unidad",
                    "factor_base": "1",
                    "precio_venta": "10.00",
                    "permite_fraccion": False,
                }
            ],
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _crear_proveedor(cliente: TestClient, cabeceras: dict, codigo: str = "PRV-VAL") -> dict:
    respuesta = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": codigo, "razon_social": "Proveedor de prueba"},
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _ingresar(
    cliente: TestClient,
    cabeceras: dict,
    producto: dict,
    almacen_id: int,
    proveedor_id: int,
) -> None:
    respuesta = cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor_id,
            "almacen_id": almacen_id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": producto["presentaciones"][0]["id"],
                    "cantidad": "100",
                    "costo_unitario": "5.00",
                    "precio_venta": "10.00",
                }
            ],
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text


def _vender(
    cliente: TestClient,
    cabeceras: dict,
    producto: dict,
    *,
    forma_pago: str | None = "efectivo",
    monto_recibido: str | None = None,
    total: str = "10.00",
    clave: str = "prueba-validacion",
) -> dict:
    cuerpo: dict = {
        "idempotency_key": clave,
        "lineas": [
            {
                "producto_id": producto["id"],
                "presentacion_id": producto["presentaciones"][0]["id"],
                "cantidad": "1",
                "precio_total": total,
            }
        ],
    }
    if forma_pago is not None:
        cuerpo["forma_pago"] = forma_pago
    if monto_recibido is not None:
        cuerpo["monto_recibido"] = monto_recibido
    respuesta = cliente.post("/api/v1/ventas", json=cuerpo, headers=cabeceras)
    return {"estado": respuesta.status_code, "cuerpo": respuesta.json()}


# --- A · El efectivo que no cubre el total ---------------------------------


def test_la_venta_se_permite_pero_registra_la_deuda(
    cliente: TestClient, cabeceras_admin: dict, unidades: dict, almacen
) -> None:
    """La venta no se rechaza, pero lo que falta por cobrar queda anotado."""
    producto = _crear_producto(cliente, cabeceras_admin, unidades)
    proveedor = _crear_proveedor(cliente, cabeceras_admin)
    _ingresar(cliente, cabeceras_admin, producto, almacen.id, proveedor["id"])

    resultado = _vender(
        cliente,
        cabeceras_admin,
        producto,
        monto_recibido="5.00",
        total="10.00",
        clave="deuda-001",
    )

    assert resultado["estado"] == 201, resultado["cuerpo"]
    venta = resultado["cuerpo"]
    assert venta["total"] == "10"
    assert venta["monto_recibido"] == "5"
    # Lo que faltaba queda registrado: no se pierde.
    assert venta["deuda"] == "5"
    # El vuelto nunca es negativo.
    assert venta["vuelto"] == "0"


def test_la_previsualizacion_avisa_de_la_deuda(
    cliente: TestClient, cabeceras_admin: dict, unidades: dict, almacen
) -> None:
    """Antes de confirmar, la caja ya sabe cuánto quedaría sin cobrar."""
    producto = _crear_producto(cliente, cabeceras_admin, unidades)
    proveedor = _crear_proveedor(cliente, cabeceras_admin)
    _ingresar(cliente, cabeceras_admin, producto, almacen.id, proveedor["id"])

    respuesta = cliente.post(
        "/api/v1/ventas/previsualizar",
        json={
            "forma_pago": "efectivo",
            "monto_recibido": "5.00",
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": producto["presentaciones"][0]["id"],
                    "cantidad": "1",
                    "precio_total": "10.00",
                }
            ],
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["deuda"] == "5"


def test_una_venta_pagada_no_deja_deuda(
    cliente: TestClient, cabeceras_admin: dict, unidades: dict, almacen
) -> None:
    """Cuando el efectivo alcanza, no hay deuda."""
    producto = _crear_producto(cliente, cabeceras_admin, unidades)
    proveedor = _crear_proveedor(cliente, cabeceras_admin)
    _ingresar(cliente, cabeceras_admin, producto, almacen.id, proveedor["id"])

    resultado = _vender(
        cliente,
        cabeceras_admin,
        producto,
        monto_recibido="20.00",
        total="10.00",
        clave="sin-deuda-001",
    )

    assert resultado["estado"] == 201, resultado["cuerpo"]
    assert resultado["cuerpo"]["vuelto"] == "10"
    assert resultado["cuerpo"]["deuda"] is None


# --- B · La forma de pago es una lista cerrada -----------------------------


def test_una_forma_de_pago_inventada_se_rechaza(
    cliente: TestClient, cabeceras_admin: dict, unidades: dict, almacen
) -> None:
    """Antes se aceptaba «credito_fantasma» y la venta quedaba confirmada."""
    producto = _crear_producto(cliente, cabeceras_admin, unidades)
    proveedor = _crear_proveedor(cliente, cabeceras_admin)
    _ingresar(cliente, cabeceras_admin, producto, almacen.id, proveedor["id"])

    resultado = _vender(
        cliente,
        cabeceras_admin,
        producto,
        forma_pago="credito_fantasma",
        clave="forma-inventada-001",
    )

    assert resultado["estado"] == 422, resultado["cuerpo"]
    mensaje = resultado["cuerpo"]["error"]["mensaje"]
    assert "efectivo" in mensaje and "yape" in mensaje


def test_las_formas_de_pago_se_publican(
    cliente: TestClient, cabeceras_vendedor: dict
) -> None:
    """El cliente lee la lista del backend: no la escribe a mano."""
    respuesta = cliente.get("/api/v1/configuracion/formas-pago", headers=cabeceras_vendedor)
    assert respuesta.status_code == 200, respuesta.text
    valores = [item["valor"] for item in respuesta.json()]
    assert valores == ["efectivo", "tarjeta", "voucher", "yape"]


# --- C · Editar un proveedor -----------------------------------------------


def test_vaciar_un_campo_lo_limpia_de_verdad(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """Antes, mandar `null` no borraba nada: el valor viejo sobrevivía."""
    alta = cliente.post(
        "/api/v1/proveedores",
        json={
            "codigo": "PRV-LIMPIEZA",
            "razon_social": "Proveedor de prueba",
            "ruc": "20512345678",
            "telefono": "01 555 0123",
            "email": "prueba@abc.com",
        },
        headers=cabeceras_admin,
    )
    assert alta.status_code == 201, alta.text
    proveedor = alta.json()

    edicion = cliente.patch(
        f"/api/v1/proveedores/{proveedor['id']}",
        json={
            "razon_social": "Proveedor de prueba",
            "ruc": None,
            "telefono": None,
            "email": None,
        },
        headers=cabeceras_admin,
    )
    assert edicion.status_code == 200, edicion.text
    resultado = edicion.json()
    assert resultado["ruc"] is None
    assert resultado["telefono"] is None
    assert resultado["email"] is None


def test_un_campo_que_no_se_envia_no_se_toca(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """Lo que no se manda se queda como estaba: el RUC sigue puesto."""
    alta = cliente.post(
        "/api/v1/proveedores",
        json={
            "codigo": "PRV-INTACTO",
            "razon_social": "Proveedor intacto",
            "ruc": "20512345679",
            "telefono": "01 555 0123",
        },
        headers=cabeceras_admin,
    )
    assert alta.status_code == 201, alta.text
    proveedor = alta.json()

    edicion = cliente.patch(
        f"/api/v1/proveedores/{proveedor['id']}",
        json={"razon_social": "Proveedor intacto renombrado"},
        headers=cabeceras_admin,
    )
    assert edicion.status_code == 200, edicion.text
    resultado = edicion.json()
    assert resultado["razon_social"] == "Proveedor intacto renombrado"
    assert resultado["ruc"] == "20512345679"
    assert resultado["telefono"] == "01 555 0123"


def test_el_ruc_repetido_se_rechaza_al_editar(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """Antes solo se comprobaba al crear: al editar, el RUC podía repetirse."""
    primero = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-RUC-A", "razon_social": "Proveedor A", "ruc": "20511111111"},
        headers=cabeceras_admin,
    )
    segundo = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-RUC-B", "razon_social": "Proveedor B", "ruc": "20522222222"},
        headers=cabeceras_admin,
    )
    assert primero.status_code == 201, primero.text
    assert segundo.status_code == 201, segundo.text

    edicion = cliente.patch(
        f"/api/v1/proveedores/{segundo.json()['id']}",
        json={"razon_social": "Proveedor B", "ruc": "20511111111"},
        headers=cabeceras_admin,
    )
    assert edicion.status_code == 400, edicion.text
    assert edicion.json()["error"]["detalle"]["campo"] == "ruc"


def test_un_ruc_con_formato_invalido_se_rechaza(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """El RUC tiene que ser de 11 dígitos."""
    respuesta = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-RUC-MAL", "razon_social": "Proveedor", "ruc": "abc"},
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "11 dígitos" in respuesta.json()["error"]["mensaje"]


def test_un_correo_con_formato_invalido_se_rechaza(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """El correo tiene que tener la forma de un correo."""
    respuesta = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-MAIL", "razon_social": "Proveedor", "email": "no-es-correo"},
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "correo" in respuesta.json()["error"]["mensaje"].lower()


# --- D · La configuración del negocio --------------------------------------


def test_la_configuracion_rechaza_un_nombre_demasiado_largo(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """Antes se guardaba un nombre de 500 caracteres: iba al ticket."""
    respuesta = cliente.put(
        "/api/v1/configuracion",
        json={"negocio_nombre": "A" * 500},
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "120" in respuesta.json()["error"]["mensaje"]


def test_la_configuracion_rechaza_un_ruc_invalido(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """Antes se guardaba un RUC «abc»."""
    respuesta = cliente.put(
        "/api/v1/configuracion",
        json={"negocio_ruc": "abc"},
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "11 dígitos" in respuesta.json()["error"]["mensaje"]


def test_la_configuracion_rechaza_un_ancho_que_no_existe(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """El ancho del ticket solo puede ser 58 o 80."""
    respuesta = cliente.put(
        "/api/v1/configuracion",
        json={"ticket_ancho": "120"},
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 422, respuesta.text


def test_la_configuracion_rechaza_un_descuento_negativo(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """Un límite de descuento negativo no tiene sentido."""
    respuesta = cliente.put(
        "/api/v1/configuracion",
        json={"venta_descuento_maximo_porcentaje": "-5"},
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 422, respuesta.text


# --- E · La importación respeta las reglas del alta ------------------------


def test_la_importacion_rechaza_un_stock_minimo_negativo(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """Antes el importador se saltaba el schema y guardaba el -500."""
    import io

    from openpyxl import Workbook

    from app.services import importador

    libro = Workbook()
    hoja = libro.active
    titulos = [importador.TITULOS[columna] for columna in importador.COLUMNAS]
    hoja.append(titulos)
    fila = {columna: "" for columna in importador.COLUMNAS}
    fila["codigo"] = "IMP-STOCK-NEG"
    fila["nombre"] = "Producto importado"
    fila["unidad_base"] = "UND"
    fila["stock_minimo"] = "-500"
    hoja.append([fila[columna] for columna in importador.COLUMNAS])
    buffer = io.BytesIO()
    libro.save(buffer)

    previsualizacion = cliente.post(
        "/api/v1/catalogo/importar/previsualizar",
        files={"archivo": ("catalogo.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    )
    assert previsualizacion.status_code == 200, previsualizacion.text
    filas = previsualizacion.json()["filas"]
    assert len(filas) == 1
    assert any("negativo" in mensaje for mensaje in filas[0]["mensajes"]), filas[0]["mensajes"]

    confirmacion = cliente.post(
        "/api/v1/catalogo/importar/confirmar",
        params={"aplicar_stock_inicial": "false"},
        files={"archivo": ("catalogo.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    )
    assert confirmacion.status_code == 200, confirmacion.text
    assert confirmacion.json()["productos_creados"] == 0
    assert confirmacion.json()["rechazadas"] == 1

    # Y el producto no debe existir con el stock negativo.
    listado = cliente.get(
        "/api/v1/catalogo/productos", params={"q": "IMP-STOCK-NEG"}, headers=cabeceras_admin
    )
    assert listado.json()["items"] == []


def test_la_importacion_rechaza_un_codigo_demasiado_largo(
    cliente: TestClient, cabeceras_admin: dict
) -> None:
    """El código del producto no puede pasar de 40 caracteres."""
    import io

    from openpyxl import Workbook

    from app.services import importador

    libro = Workbook()
    hoja = libro.active
    titulos = [importador.TITULOS[columna] for columna in importador.COLUMNAS]
    hoja.append(titulos)
    fila = {columna: "" for columna in importador.COLUMNAS}
    fila["codigo"] = "X" * 60
    fila["nombre"] = "Producto con código largo"
    fila["unidad_base"] = "UND"
    hoja.append([fila[columna] for columna in importador.COLUMNAS])
    buffer = io.BytesIO()
    libro.save(buffer)

    previsualizacion = cliente.post(
        "/api/v1/catalogo/importar/previsualizar",
        files={"archivo": ("catalogo.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=cabeceras_admin,
    )
    assert previsualizacion.status_code == 200, previsualizacion.text
    filas = previsualizacion.json()["filas"]
    assert any("40 caracteres" in mensaje for mensaje in filas[0]["mensajes"]), filas[0]["mensajes"]
