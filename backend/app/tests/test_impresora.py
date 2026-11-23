"""Pruebas de la impresora de tickets y de la configuración del negocio."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.impresora import (
    ConfigImpresora,
    ConstructorTicket,
    ErrorImpresora,
    comprobar,
    consultar_estado,
)


# --- Construcción del ticket ------------------------------------------------
def test_el_ticket_inicia_con_el_reinicio_y_tabla_de_caracteres():
    constructor = ConstructorTicket(ConfigImpresora(columnas=48)).reiniciar().tabla_caracteres()
    datos = constructor.bytes()
    assert datos.startswith(b"\x1b@")  # ESC @
    assert b"\x1bt\x02" in datos  # ESC t 2 (PC850)


def test_el_ticket_alinea_centrado_y_a_la_derecha():
    constructor = ConstructorTicket(ConfigImpresora(columnas=32))
    constructor.centro("CENTRO").derecha("DERECHA")
    datos = constructor.bytes()
    assert b"\x1b-\x01" in datos  # ESC - 1 (centro)
    assert b"\x1b-\x02" in datos  # ESC - 2 (derecha)


def test_el_ticket_genera_codigo_qr():
    constructor = ConstructorTicket(ConfigImpresora(columnas=32, qr=True))
    constructor.codigo_qr("V-000123")
    datos = constructor.bytes()
    assert b"\x1d( k" in datos  # GS ( k
    assert b"V-000123" in datos


def test_el_ticket_corta_el_papel():
    constructor = ConstructorTicket(ConfigImpresora(columnas=32, cortar=True))
    constructor.cortar()
    assert b"\x1dV" in constructor.bytes()


def test_el_ticket_sin_corte_avanza_el_papel():
    constructor = ConstructorTicket(ConfigImpresora(columnas=32, cortar=False))
    constructor.cortar()
    assert b"\x1dV" not in constructor.bytes()


def test_el_ticket_acepta_acentos():
    constructor = ConstructorTicket(ConfigImpresora(columnas=48))
    constructor.linea("Acentos: áéíóúñ ¿ ¡")
    assert "Acentos" in constructor.bytes().decode("cp850", errors="replace")


# --- Estado de la impresora -------------------------------------------------
def test_estado_de_impresora_desactivada():
    resultado = comprobar(ConfigImpresora(activa=False))
    assert resultado["activa"] is False
    assert resultado["conectada"] is False
    assert resultado["motivo"] == "desactivada"


def test_estado_de_impresora_inalcanzable():
    resultado = comprobar(
        ConfigImpresora(activa=True, host="127.0.0.1", puerto=9, tiempo_limite=1)
    )
    assert resultado["activa"] is True
    assert resultado["conectada"] is False
    assert resultado["motivo"] in {"rechazada", "timeout", "sin_ruta"}


def test_la_comprobacion_no_envia_nada_a_la_impresora(monkeypatch):
    """Conectar y comprobar **no imprime**: no se envía ni un byte."""
    enviados: list[bytes] = []

    class ConexionFalsa:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def sendall(self, datos):
            enviados.append(datos)

        def settimeout(self, _):
            pass

    monkeypatch.setattr(
        "app.services.impresora.socket.create_connection", lambda *a, **k: ConexionFalsa()
    )
    resultado = comprobar(ConfigImpresora(activa=True, host="127.0.0.1", puerto=9100))
    assert resultado["conectada"] is True
    assert resultado["motivo"] == "ok"
    assert resultado["tiempo_ms"] is not None
    assert enviados == [], "la comprobación no debe enviar nada a la impresora"


def test_la_consulta_de_estado_no_imprime(monkeypatch):
    """La consulta de estado pregunta, pero no imprime."""
    enviados: list[bytes] = []

    class ConexionFalsa:
        def __init__(self, respuesta: bytes):
            self.respuesta = respuesta

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def sendall(self, datos):
            enviados.append(datos)

        def settimeout(self, _):
            pass

        def recv(self, _):
            return self.respuesta

    monkeypatch.setattr(
        "app.services.impresora.socket.create_connection",
        lambda *a, **k: ConexionFalsa(b"\x00"),
    )
    resultado = consultar_estado(ConfigImpresora(activa=True, host="127.0.0.1", puerto=9100))
    assert resultado["respondio"] is True
    assert resultado["byte"] == 0
    assert resultado["avisos"] == []
    assert enviados == [b"\x1bi\x01"]

    # Un byte con bits de problema se traduce a avisos legibles.
    monkeypatch.setattr(
        "app.services.impresora.socket.create_connection",
        lambda *a, **k: ConexionFalsa(b"\x18"),
    )
    con_avisos = consultar_estado(ConfigImpresora(activa=True, host="127.0.0.1", puerto=9100))
    assert "atasco de papel" in con_avisos["avisos"]
    assert "tapa abierta" in con_avisos["avisos"]


def test_la_consulta_de_estado_avisa_si_el_equipo_no_responde(monkeypatch):
    class ConexionFalsa:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def sendall(self, _):
            pass

        def settimeout(self, _):
            pass

        def recv(self, _):
            return b""

    monkeypatch.setattr(
        "app.services.impresora.socket.create_connection", lambda *a, **k: ConexionFalsa()
    )
    resultado = consultar_estado(ConfigImpresora(activa=True, host="127.0.0.1", puerto=9100))
    assert resultado["respondio"] is False
    assert "no respondió" in resultado["mensaje"]


# --- Endpoints --------------------------------------------------------------
def test_el_estado_de_la_impresora_da_diagnostico_y_especificaciones(
    cliente, cabeceras_admin
):
    """El estado dice si responde, por qué y con qué especificaciones."""
    cliente.put(
        "/api/v1/configuracion",
        json={
            "impresora_modelo": "CBX-POS88E",
            "impresora_ancho_mm": "80",
            "impresora_resolucion": "203",
        },
        headers=cabeceras_admin,
    )

    respuesta = cliente.get("/api/v1/impresora/estado", headers=cabeceras_admin)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["modelo"] == "CBX-POS88E"
    assert cuerpo["ancho_mm"] == "80"
    assert cuerpo["resolucion"] == "203"
    assert "conectada" in cuerpo
    assert "motivo" in cuerpo
    assert "mensaje" in cuerpo
    # Sin pedir la consulta, no se consulta el estado del equipo.
    assert "estado_equipo" not in cuerpo

    con_estado = cliente.get(
        "/api/v1/impresora/estado", params={"consultar": "true"}, headers=cabeceras_admin
    )
    assert "estado_equipo" in con_estado.json()


def test_la_configuracion_rechaza_especificaciones_invalidas(cliente, cabeceras_admin):
    """El ancho y la resolución de la impresora son de una lista cerrada."""
    ancho = cliente.put(
        "/api/v1/configuracion",
        json={"impresora_ancho_mm": "120"},
        headers=cabeceras_admin,
    )
    assert ancho.status_code == 422

    resolucion = cliente.put(
        "/api/v1/configuracion",
        json={"impresora_resolucion": "600"},
        headers=cabeceras_admin,
    )
    assert resolucion.status_code == 422


def test_configuracion_del_negocio_lectura_y_guardado(cliente, cabeceras_admin):
    lectura = cliente.get("/api/v1/configuracion", headers=cabeceras_admin)
    assert lectura.status_code == 200
    valores = lectura.json()["valores"]
    assert "negocio_nombre" in valores
    assert valores["venta_descuento_maximo_porcentaje"] == "20"

    guardado = cliente.put(
        "/api/v1/configuracion",
        json={
            "negocio_nombre": "Almacén Vivo SAC",
            "negocio_ruc": "20512345678",
            "ticket_pie": "¡Gracias!",
            "venta_descuento_maximo_porcentaje": "30",
        },
        headers=cabeceras_admin,
    )
    assert guardado.status_code == 200
    assert guardado.json()["valores"]["negocio_nombre"] == "Almacén Vivo SAC"
    assert guardado.json()["valores"]["venta_descuento_maximo_porcentaje"] == "30"


def test_configuracion_rechaza_valores_no_validos(cliente, cabeceras_admin):
    """La configuración se valida con su schema: el ancho del ticket es 58 o 80."""
    respuesta = cliente.put(
        "/api/v1/configuracion",
        json={"ticket_ancho": "120"},
        headers=cabeceras_admin,
    )
    assert respuesta.status_code == 422
    assert "58" in respuesta.json()["error"]["mensaje"]


def test_configuracion_solo_el_administrador_la_modifica(cliente, cabeceras_vendedor):
    respuesta = cliente.put(
        "/api/v1/configuracion",
        json={"negocio_nombre": "X"},
        headers=cabeceras_vendedor,
    )
    assert respuesta.status_code == 403


def test_impresora_desactivada_no_imprime(cliente, cabeceras_admin):
    respuesta = cliente.post("/api/v1/impresora/prueba", headers=cabeceras_admin)
    assert respuesta.status_code == 503
    assert respuesta.json()["error"]["codigo"] == "error_impresora"


def test_impresion_del_ticket_de_una_venta(
    cliente, cabeceras_admin, cabeceras_vendedor, unidades, almacen, monkeypatch
):
    """La venta se registra, el ticket sale y la venta queda como impresa."""
    from app.services import tickets

    enviados: list[bytes] = []

    def _enviar_falso(datos, config=None):
        enviados.append(datos)

    monkeypatch.setattr(tickets, "enviar", _enviar_falso)

    producto = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "IMP-001",
            "nombre": "Gaseosa 500 ml",
            "unidad_base_id": unidades["UND"].id,
            "presentaciones": [
                {"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"}
            ],
        },
        headers=cabeceras_admin,
    ).json()
    presentacion = producto["presentaciones"][0]

    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-IMP", "razon_social": "Distribuidora SAC"},
        headers=cabeceras_admin,
    ).json()
    cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor["id"],
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "10",
                    "costo_unitario": "2.00",
                }
            ],
        },
        headers=cabeceras_admin,
    )

    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "forma_pago": "efectivo",
            "monto_recibido": "10",
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "2",
                }
            ],
        },
        headers=cabeceras_vendedor,
    ).json()

    assert venta["total"] == "5"
    assert venta["forma_pago"] == "efectivo"
    assert venta["monto_recibido"] == "10"
    assert venta["vuelto"] == "5"
    assert venta["ticket_impreso"] is False

    respuesta = cliente.post(
        f"/api/v1/ventas/{venta['id']}/imprimir", headers=cabeceras_vendedor
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["ok"] is True
    assert len(enviados) == 1
    assert b"Gaseosa" in enviados[0]

    detalle = cliente.get(f"/api/v1/ventas/{venta['id']}", headers=cabeceras_vendedor).json()
    assert detalle["ticket_impreso"] is True
    assert detalle["impresion_error"] is None

    # Reimpresión: se vuelve a enviar y queda registrado.
    reimpresion = cliente.post(
        f"/api/v1/ventas/{venta['id']}/imprimir", headers=cabeceras_vendedor
    )
    assert reimpresion.status_code == 200
    assert reimpresion.json()["reimpresion"] is True
    assert len(enviados) == 2


def test_el_ticket_expresa_los_balanceados_en_kilos(
    cliente, cabeceras_admin, cabeceras_vendedor, unidades, almacen, monkeypatch
):
    """Los productos a granel por peso se leen en kilos, no en sacos.

    «15 kg x S/ 2,86» se entiende; «0.375 x S/ 114,40» no.
    """
    from app.services import tickets

    enviados: list[bytes] = []

    def _enviar_falso(datos, config=None):
        enviados.append(datos)

    monkeypatch.setattr(tickets, "enviar", _enviar_falso)

    producto = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "BAL-001",
            "nombre": "Terneros Cuna",
            "unidad_base_id": unidades["GR"].id,
            "presentaciones": [
                {
                    "nombre": "saco 40 kg pellet",
                    "factor_base": "40000",
                    "precio_venta": "114.40",
                    # El balanceado se vende a granel, por kilos.
                    "permite_fraccion": True,
                }
            ],
        },
        headers=cabeceras_admin,
    ).json()
    presentacion = producto["presentaciones"][0]
    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-BAL", "razon_social": "Distribuidora SAC"},
        headers=cabeceras_admin,
    ).json()
    cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor["id"],
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "10",
                    "costo_unitario": "88.00",
                }
            ],
        },
        headers=cabeceras_admin,
    )

    # 0.375 de saco = 15 kg.
    respuesta_venta = cliente.post(
        "/api/v1/ventas",
        json={
            "forma_pago": "efectivo",
            "monto_recibido": "50",
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "0.375",
                    "precio_total": "42.90",
                }
            ],
        },
        headers=cabeceras_vendedor,
    )
    assert respuesta_venta.status_code == 201, respuesta_venta.text
    venta = respuesta_venta.json()

    # El ticket se arma al imprimir.
    cliente.post(f"/api/v1/ventas/{venta['id']}/imprimir", headers=cabeceras_vendedor)

    assert len(enviados) == 1
    texto = enviados[0].decode("utf-8", errors="replace")
    assert "15 kg" in texto
    assert "2,86" in texto


def test_fallo_de_impresora_no_pierde_la_venta(
    cliente, cabeceras_admin, cabeceras_vendedor, unidades, almacen, monkeypatch
):
    """Si la impresora falla, la venta sigue registrada y se puede reintentar."""
    from app.services import tickets

    def _enviar_falso(datos, config=None):
        raise ErrorImpresora("No se pudo conectar con la impresora.")

    monkeypatch.setattr(tickets, "enviar", _enviar_falso)

    producto = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "IMP-002",
            "nombre": "Leche 400 g",
            "unidad_base_id": unidades["UND"].id,
            "presentaciones": [
                {"nombre": "unidad", "factor_base": "1", "precio_venta": "4.50"}
            ],
        },
        headers=cabeceras_admin,
    ).json()
    presentacion = producto["presentaciones"][0]
    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-IMP2", "razon_social": "Distribuidora SAC"},
        headers=cabeceras_admin,
    ).json()
    cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor["id"],
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "5",
                    "costo_unitario": "3.80",
                }
            ],
        },
        headers=cabeceras_admin,
    )
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "1",
                }
            ],
        },
        headers=cabeceras_vendedor,
    ).json()

    fallo = cliente.post(
        f"/api/v1/ventas/{venta['id']}/imprimir", headers=cabeceras_vendedor
    )
    assert fallo.status_code == 503

    detalle = cliente.get(f"/api/v1/ventas/{venta['id']}", headers=cabeceras_vendedor).json()
    assert detalle["estado"] == "CONFIRMADO"
    assert detalle["ticket_impreso"] is False
    assert detalle["impresion_error"]


def test_el_ticket_muestra_el_precio_original_si_cambio(
    cliente, cabeceras_admin, unidades, almacen
):
    producto = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "IMP-003",
            "nombre": "Producto con descuento",
            "unidad_base_id": unidades["UND"].id,
            "presentaciones": [
                {"nombre": "unidad", "factor_base": "1", "precio_venta": "10.00"}
            ],
        },
        headers=cabeceras_admin,
    ).json()
    presentacion = producto["presentaciones"][0]
    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-IMP3", "razon_social": "Distribuidora SAC"},
        headers=cabeceras_admin,
    ).json()
    cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor["id"],
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "5",
                    "costo_unitario": "8.00",
                }
            ],
        },
        headers=cabeceras_admin,
    )
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "1",
                    "precio_unitario": "8.00",
                    "motivo_precio": "Promoción",
                }
            ],
        },
        headers=cabeceras_admin,
    ).json()

    texto = cliente.get(
        f"/api/v1/impresora/ticket/{venta['id']}", headers=cabeceras_admin
    ).json()["texto"]
    assert "precio de lista" in texto
    assert "Promoción" in texto
    assert "TOTAL" in texto
