"""Pruebas de integración del flujo completo (plan §11.1 · T01–T18)."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient


# --- Utilidades de apoyo ---------------------------------------------------
def crear_producto(
    cliente: TestClient,
    cabeceras: dict,
    unidades: dict,
    *,
    codigo: str = "P001",
    nombre: str = "Arroz a granel",
    unidad: str = "GR",
    presentaciones: list[dict] | None = None,
    stock_minimo: str = "0",
    permite_fraccion: bool = False,
) -> dict:
    payload = {
        "codigo": codigo,
        "nombre": nombre,
        "unidad_base_id": unidades[unidad].id,
        "stock_minimo_base": stock_minimo,
        "permite_fraccion": permite_fraccion,
        "presentaciones": presentaciones
        if presentaciones is not None
        else [
            {"nombre": "1 kg", "factor_base": "1000", "precio_venta": "5.00", "permite_fraccion": True},
            {"nombre": "saco 50 kg", "factor_base": "50000", "precio_venta": "180.00"},
        ],
    }
    respuesta = cliente.post("/api/v1/catalogo/productos", json=payload, headers=cabeceras)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def crear_proveedor(cliente: TestClient, cabeceras: dict, codigo: str = "PRV01") -> dict:
    respuesta = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": codigo, "razon_social": "Mayorista Central SAC"},
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def abbreviaturas_presentaciones(producto: dict) -> dict[str, int]:
    return {p["nombre"]: p["id"] for p in producto["presentaciones"]}


def ingresar(
    cliente: TestClient,
    cabeceras: dict,
    proveedor_id: int,
    almacen_id: int,
    lineas: list[dict],
    documento: str | None = None,
) -> dict:
    respuesta = cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor_id,
            "almacen_id": almacen_id,
            "documento": documento,
            "lineas": lineas,
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def stock(cliente: TestClient, cabeceras: dict, producto_id: int, almacen_id: int) -> str:
    respuesta = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": almacen_id, "q": ""},
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text
    for item in respuesta.json()["items"]:
        if item["producto_id"] == producto_id:
            return item["cantidad_base"]
    return "0"


# --- Catálogo --------------------------------------------------------------
def test_t01_crear_producto_con_presentacion(cliente, cabeceras_admin, unidades):
    producto = crear_producto(cliente, cabeceras_admin, unidades)
    assert producto["codigo"] == "P001"
    assert len(producto["presentaciones"]) == 2
    assert producto["presentaciones"][0]["factor_base"] == "1000"


def test_t02_codigo_interno_duplicado(cliente, cabeceras_admin, unidades):
    crear_producto(cliente, cabeceras_admin, unidades, codigo="DUP")
    respuesta = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "dup",
            "nombre": "Otro producto",
            "unidad_base_id": unidades["GR"].id,
            "presentaciones": [{"nombre": "1 kg", "factor_base": "1000"}],
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["codigo"] == "error_negocio"


def test_t03_producto_con_dos_proveedores(cliente, cabeceras_admin, unidades):
    producto = crear_producto(cliente, cabeceras_admin, unidades, codigo="MP001")
    proveedor_a = crear_proveedor(cliente, cabeceras_admin, "PRV-A")
    proveedor_b = crear_proveedor(cliente, cabeceras_admin, "PRV-B")
    for proveedor in (proveedor_a, proveedor_b):
        respuesta = cliente.post(
            "/api/v1/proveedores/vinculos",
            json={"producto_id": producto["id"], "proveedor_id": proveedor["id"], "habitual": True},
            headers=cabeceras_admin,
        )
        assert respuesta.status_code == 201, respuesta.text
    productos = cliente.get(
        f"/api/v1/proveedores/{proveedor_a['id']}/productos", headers=cabeceras_admin
    ).json()
    assert len(productos) == 1
    productos_b = cliente.get(
        f"/api/v1/proveedores/{proveedor_b['id']}/productos", headers=cabeceras_admin
    ).json()
    assert len(productos_b) == 1


# --- Abastecimiento y conversiones ----------------------------------------
def test_t04_cinco_cajas_de_24_unidades(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="GAS500",
        nombre="Gaseosa 500 ml",
        unidad="UND",
        presentaciones=[
            {"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"},
            {"nombre": "paquete x6", "factor_base": "6", "precio_venta": "13.50"},
            {"nombre": "caja x24", "factor_base": "24", "precio_venta": "50.00"},
        ],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingreso = ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["caja x24"], "cantidad": "5", "costo_unitario": "48.00"}],
    )
    assert ingreso["detalles"][0]["cantidad_base"] == "120"
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "120"


def test_t05_tres_sacos_de_50_kg(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(cliente, cabeceras_admin, unidades, codigo="ARROZ")
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingreso = ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["saco 50 kg"], "cantidad": "3", "costo_unitario": "170.00"}],
    )
    assert ingreso["detalles"][0]["cantidad_base"] == "150000"
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "150000"

    # El costo por unidad base conserva precisión (S/ 170.00 por saco de 50 kg
    # equivale a S/ 0.0034 por gramo).
    existencias = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": almacen.id},
        headers=cabeceras_admin,
    ).json()
    item = next(i for i in existencias["items"] if i["producto_id"] == producto["id"])
    assert item["costo_promedio_base"] == "0.0034"


def test_t08_venta_superior_al_stock_rechazada(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(cliente, cabeceras_admin, unidades, codigo="LIMIT")
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["1 kg"], "cantidad": "2", "costo_unitario": "5.00"}],
    )
    respuesta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": ids["1 kg"],
                    "cantidad": "3",
                }
            ],
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "stock_insuficiente"
    # No se creó una venta parcial
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "2000"


# --- Ventas ----------------------------------------------------------------
def test_t06_venta_fraccionada_en_kilos(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(cliente, cabeceras_admin, unidades, codigo="ARROZ2")
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["saco 50 kg"], "cantidad": "1", "costo_unitario": "170.00"}],
    )
    respuesta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {"producto_id": producto["id"], "presentacion_id": ids["1 kg"], "cantidad": "0.750"}
            ],
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["detalles"][0]["cantidad_base"] == "750"
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "49250"


def test_t07_venta_de_media_unidad_indivisible(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="INDIV",
        nombre="Jabón en barra",
        unidad="UND",
        presentaciones=[{"nombre": "barra", "factor_base": "1", "precio_venta": "3.00"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["barra"], "cantidad": "10", "costo_unitario": "2.00"}],
    )
    respuesta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {"producto_id": producto["id"], "presentacion_id": ids["barra"], "cantidad": "0.5"}
            ],
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["codigo"] == "unidad_invalida"


def test_t10_idempotencia_de_confirmacion(cliente, cabeceras_admin, unidades, almacen, clave_idempotencia):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="IDEM",
        nombre="Gaseosa 500 ml",
        unidad="UND",
        presentaciones=[{"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["botella"], "cantidad": "10", "costo_unitario": "2.00"}],
    )
    payload = {
        "almacen_id": almacen.id,
        "idempotency_key": clave_idempotencia,
        "lineas": [
            {"producto_id": producto["id"], "presentacion_id": ids["botella"], "cantidad": "2"}
        ],
    }
    primera = cliente.post("/api/v1/ventas", json=payload, headers=cabeceras_admin)
    segunda = cliente.post("/api/v1/ventas", json=payload, headers=cabeceras_admin)
    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert primera.json()["numero"] == segunda.json()["numero"]
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "8"


def test_t12_anular_venta_restituye_stock(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="ANUL",
        nombre="Gaseosa 500 ml",
        unidad="UND",
        presentaciones=[{"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["botella"], "cantidad": "10", "costo_unitario": "2.00"}],
    )
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {"producto_id": producto["id"], "presentacion_id": ids["botella"], "cantidad": "3"}
            ],
        },
        headers=cabeceras_admin,
    ).json()
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "7"

    anulacion = cliente.post(
        f"/api/v1/ventas/{venta['id']}/anular",
        json={"motivo": "Error de digitación en caja"},
        headers=cabeceras_admin,
    )
    assert anulacion.status_code == 200, anulacion.text
    assert anulacion.json()["estado"] == "ANULADO"
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "10"

    # La huella histórica se conserva
    movimientos = cliente.get(
        "/api/v1/inventario/movimientos",
        params={"producto_id": producto["id"]},
        headers=cabeceras_admin,
    ).json()
    tipos = {m["tipo"] for m in movimientos["items"]}
    assert {"ABASTECIMIENTO", "VENTA", "REVERSO_VENTA"} <= tipos


def test_t13_anular_dos_veces_rechazado(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="ANUL2",
        unidad="UND",
        presentaciones=[{"nombre": "unidad", "factor_base": "1", "precio_venta": "1.00"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "5", "costo_unitario": "1.00"}],
    )
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "1"}
            ],
        },
        headers=cabeceras_admin,
    ).json()
    cliente.post(
        f"/api/v1/ventas/{venta['id']}/anular",
        json={"motivo": "Anulación de prueba"},
        headers=cabeceras_admin,
    )
    segunda = cliente.post(
        f"/api/v1/ventas/{venta['id']}/anular",
        json={"motivo": "Anulación de prueba repetida"},
        headers=cabeceras_admin,
    )
    assert segunda.status_code == 400


def test_t14_cambiar_precio_no_altera_ventas(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="PRECIO",
        nombre="Gaseosa 500 ml",
        unidad="UND",
        presentaciones=[{"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["botella"], "cantidad": "10", "costo_unitario": "2.00"}],
    )
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {"producto_id": producto["id"], "presentacion_id": ids["botella"], "cantidad": "1"}
            ],
        },
        headers=cabeceras_admin,
    ).json()
    cliente.patch(
        f"/api/v1/catalogo/presentaciones/{ids['botella']}",
        json={"precio_venta": "3.75"},
        headers=cabeceras_admin,
    )
    detalle = cliente.get(f"/api/v1/ventas/{venta['id']}", headers=cabeceras_admin).json()
    assert detalle["detalles"][0]["precio_unitario"] == "2.5"
    assert detalle["total"] == "2.5"


def test_t15_cambiar_factor_no_altera_historial(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="FACTOR",
        unidad="UND",
        presentaciones=[{"nombre": "caja x10", "factor_base": "10", "precio_venta": "20.00"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingreso = ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["caja x10"], "cantidad": "2", "costo_unitario": "18.00"}],
    )
    cliente.patch(
        f"/api/v1/catalogo/presentaciones/{ids['caja x10']}",
        json={"factor_base": "12"},
        headers=cabeceras_admin,
    )
    historial = cliente.get(
        f"/api/v1/abastecimientos/{ingreso['id']}", headers=cabeceras_admin
    ).json()
    assert historial["detalles"][0]["cantidad_base"] == "20"
    assert historial["detalles"][0]["factor_snapshot"] == "10"


def test_t16_vendedor_puede_ajustar_precio_dentro_del_limite(
    cliente, cabeceras_admin, cabeceras_vendedor, unidades, almacen
):
    """El precio lo ajusta quien vende, dentro del límite configurado."""
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="PRECIOV",
        nombre="Gaseosa 500 ml",
        unidad="UND",
        presentaciones=[{"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin, "PRV-PREC")
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["botella"], "cantidad": "10", "costo_unitario": "2.00"}],
    )

    # El vendedor puede ajustar el precio dentro del límite (20 %).
    venta_vendedor = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": ids["botella"],
                    "cantidad": "1",
                    "precio_unitario": "2.00",
                    "motivo_precio": "Promoción",
                }
            ],
        },
        headers=cabeceras_vendedor,
    )
    assert venta_vendedor.status_code == 201, venta_vendedor.text
    cuerpo = venta_vendedor.json()
    assert cuerpo["detalles"][0]["precio_unitario"] == "2"
    assert cuerpo["detalles"][0]["precio_original"] == "2.5"
    assert cuerpo["detalles"][0]["motivo_precio"] == "Promoción"
    assert cuerpo["total"] == "2"

    # Por encima del límite, el vendedor no puede: la venta se rechaza.
    venta_excesiva = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": ids["botella"],
                    "cantidad": "1",
                    "precio_unitario": "0.10",
                }
            ],
        },
        headers=cabeceras_vendedor,
    )
    assert venta_excesiva.status_code == 409, venta_excesiva.text
    assert venta_excesiva.json()["error"]["codigo"] == "precio_fuera_de_limite"

    # El administrador sí puede superarlo.
    venta_admin = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": ids["botella"],
                    "cantidad": "1",
                    "precio_unitario": "1.00",
                }
            ],
        },
        headers=cabeceras_admin,
    )
    assert venta_admin.status_code == 201, venta_admin.text
    assert venta_admin.json()["detalles"][0]["precio_unitario"] == "1"
    assert venta_admin.json()["total"] == "1"


def test_t16_vendedor_no_puede_crear_productos(cliente, cabeceras_vendedor, unidades):
    respuesta = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "NO",
            "nombre": "No permitido",
            "unidad_base_id": unidades["UND"].id,
            "presentaciones": [{"nombre": "unidad", "factor_base": "1"}],
        },
        headers=cabeceras_vendedor,
    )
    assert respuesta.status_code == 403


def test_t16_vendedor_no_puede_anular_ventas(cliente, cabeceras_admin, cabeceras_vendedor, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="ANULV",
        unidad="UND",
        presentaciones=[{"nombre": "unidad", "factor_base": "1", "precio_venta": "1.00"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "5", "costo_unitario": "1.00"}],
    )
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "1"}
            ],
        },
        headers=cabeceras_vendedor,
    ).json()
    respuesta = cliente.post(
        f"/api/v1/ventas/{venta['id']}/anular",
        json={"motivo": "Intento no autorizado"},
        headers=cabeceras_vendedor,
    )
    assert respuesta.status_code == 403


def test_t17_producto_desactivado_conserva_historial(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="DESACT",
        unidad="UND",
        presentaciones=[{"nombre": "unidad", "factor_base": "1", "precio_venta": "1.00"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    # Primero se registra el histórico con el producto activo.
    ingreso = ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "2", "costo_unitario": "1.00"}],
    )
    assert ingreso["estado"] == "CONFIRMADO"

    cliente.patch(
        f"/api/v1/catalogo/productos/{producto['id']}",
        json={"activo": False},
        headers=cabeceras_admin,
    )

    # Ya no es seleccionable para nuevas operaciones...
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "1"}
            ],
        },
        headers=cabeceras_admin,
    )
    assert venta.status_code == 400
    assert "desactivado" in venta.json()["error"]["mensaje"].lower()

    # ...pero el histórico permanece intacto.
    movimientos = cliente.get(
        "/api/v1/inventario/movimientos",
        params={"producto_id": producto["id"]},
        headers=cabeceras_admin,
    ).json()
    assert movimientos["total"] == 1
    assert movimientos["items"][0]["tipo"] == "ABASTECIMIENTO"

    producto_activo = cliente.get(
        f"/api/v1/catalogo/productos/{producto['id']}", headers=cabeceras_admin
    ).json()
    assert producto_activo["activo"] is False
    assert len(producto_activo["presentaciones"]) == 1


def test_conciliacion_sin_diferencias(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="CONC",
        unidad="UND",
        presentaciones=[{"nombre": "unidad", "factor_base": "1", "precio_venta": "1.00"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "5", "costo_unitario": "1.00"}],
    )
    conciliacion = cliente.get("/api/v1/inventario/conciliacion", headers=cabeceras_admin).json()
    assert conciliacion["diferencias"] == []
    assert conciliacion["existencias_negativas"] == []


def test_ajuste_administrativo_registrado(cliente, cabeceras_admin, unidades, almacen):
    producto = crear_producto(
        cliente,
        cabeceras_admin,
        unidades,
        codigo="AJUS",
        unidad="UND",
        presentaciones=[{"nombre": "unidad", "factor_base": "1", "precio_venta": "1.00"}],
    )
    ids = abbreviaturas_presentaciones(producto)
    proveedor = crear_proveedor(cliente, cabeceras_admin)
    ingresar(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        [{"producto_id": producto["id"], "presentacion_id": ids["unidad"], "cantidad": "10", "costo_unitario": "1.00"}],
    )
    respuesta = cliente.post(
        "/api/v1/inventario/ajustes",
        json={
            "almacen_id": almacen.id,
            "producto_id": producto["id"],
            "cantidad_base": "-2",
            "motivo": "Rotura de dos unidades durante el manipuleo",
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 201, respuesta.text
    assert stock(cliente, cabeceras_admin, producto["id"], almacen.id) == "8"


