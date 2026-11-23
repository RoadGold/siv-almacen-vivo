"""Pruebas del inventario por lotes con precios de venta independientes.

Escenarios (documento de requerimiento, pruebas 1 a 13).
"""

from __future__ import annotations

import threading
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Almacen,
    Dimension,
    LoteInventario,
    Producto,
    PresentacionProducto,
    UnidadMedida,
    Usuario,
)


def _producto(cliente, cabeceras, unidades, codigo="LOT-001", nombre="Detergente Bolívar 900 g"):
    return cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": codigo,
            "nombre": nombre,
            "unidad_base_id": unidades["UND"].id,
            "presentaciones": [
                {"nombre": "botella", "factor_base": "1", "precio_venta": "12.00"},
                {"nombre": "caja x12", "factor_base": "12", "precio_venta": "140.00"},
            ],
        },
        headers=cabeceras,
    ).json()


def _ingreso(
    cliente,
    cabeceras,
    proveedor_id,
    almacen_id,
    producto,
    presentacion,
    cantidad,
    costo,
    precio=None,
):
    respuesta = cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor_id,
            "almacen_id": almacen_id,
            "documento": "F001-LOTES",
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": cantidad,
                    "costo_unitario": costo,
                    "precio_venta": precio,
                }
            ],
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _lotes(cliente, cabeceras, producto_id):
    return cliente.get(f"/api/v1/lotes/producto/{producto_id}", headers=cabeceras).json()


@pytest.fixture
def base(cliente, cabeceras_admin, cabeceras_vendedor, unidades, almacen):
    """Producto con un primer lote de 10 unidades a S/ 8.00 (precio S/ 12.00)."""
    producto = _producto(cliente, cabeceras_admin, unidades)
    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-LOT", "razon_social": "Distribuidora SAC"},
        headers=cabeceras_admin,
    ).json()
    presentacion = producto["presentaciones"][0]
    ingreso = _ingreso(
        cliente,
        cabeceras_admin,
        proveedor["id"],
        almacen.id,
        producto,
        presentacion,
        "10",
        "8.00",
        "12.00",
    )
    return {
        "producto": producto,
        "proveedor": proveedor,
        "presentacion": presentacion,
        "almacen_id": almacen.id,
        "ingreso": ingreso,
        "vendedor": cabeceras_vendedor,
        "admin": cabeceras_admin,
    }


# --- Prueba 1: crear producto con un lote inicial --------------------------
def test_1_el_ingreso_crea_el_lote_inicial(base, cliente):
    lotes = _lotes(cliente, base["admin"], base["producto"]["id"])
    assert len(lotes) == 1
    lote = lotes[0]
    assert lote["cantidad_disponible"] == "10"
    assert lote["costo_base"] == "8"
    assert lote["precio_venta"] == "12"
    assert lote["estado"] == "ACTIVO"
    assert lote["origen"] == "RECEPCION"


# --- Prueba 2: nuevo ingreso no toca el lote anterior ----------------------
def test_2_nuevo_ingreso_crea_otro_lote_sin_tocar_el_anterior(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert len(lotes) == 2
    # El lote viejo conserva su costo y su precio.
    assert lotes[0]["cantidad_disponible"] == "10"
    assert lotes[0]["costo_base"] == "8"
    assert lotes[0]["precio_venta"] == "12"
    # El nuevo tiene los suyos.
    assert lotes[1]["cantidad_disponible"] == "20"
    assert lotes[1]["costo_base"] == "9.5"
    assert lotes[1]["precio_venta"] == "14"
    # El stock consolidado del producto es la suma de los lotes.
    existencias = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": base["almacen_id"], "q": producto["codigo"]},
        headers=base["admin"],
    ).json()
    assert existencias["items"][0]["cantidad_base"] == "30"


# --- Prueba 3: venta del lote antiguo ---------------------------------------
def test_3_la_venta_del_lote_antiguo_solo_baja_ese_lote(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": base["almacen_id"],
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "2",
                    "lote_id": lotes[0]["id"],
                }
            ],
        },
        headers=base["vendedor"],
    )
    assert venta.status_code == 201, venta.text
    cuerpo = venta.json()
    # Se cobra el precio del lote antiguo.
    assert cuerpo["detalles"][0]["precio_unitario"] == "12"
    assert cuerpo["total"] == "24"
    assert cuerpo["detalles"][0]["lote_id"] == lotes[0]["id"]

    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert lotes[0]["cantidad_disponible"] == "8"
    assert lotes[1]["cantidad_disponible"] == "20"


# --- Prueba 4: venta de un lote nuevo sin agotar el anterior ----------------
def test_4_se_puede_vender_el_lote_nuevo_sin_agotar_el_viejo(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": base["almacen_id"],
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "3",
                    "lote_id": lotes[1]["id"],
                }
            ],
        },
        headers=base["vendedor"],
    )
    assert venta.status_code == 201, venta.text
    assert venta.json()["detalles"][0]["precio_unitario"] == "14"

    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert lotes[0]["cantidad_disponible"] == "10"
    assert lotes[1]["cantidad_disponible"] == "17"


# --- Prueba 5: venta combinada de dos lotes --------------------------------
def test_5_venta_combinada_de_dos_lotes_del_mismo_producto(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": base["almacen_id"],
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "2",
                    "lote_id": lotes[0]["id"],
                },
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "3",
                    "lote_id": lotes[1]["id"],
                },
            ],
        },
        headers=base["vendedor"],
    )
    assert venta.status_code == 201, venta.text
    cuerpo = venta.json()
    # Cada línea con su precio.
    assert cuerpo["detalles"][0]["precio_unitario"] == "12"
    assert cuerpo["detalles"][1]["precio_unitario"] == "14"
    assert cuerpo["total"] == "66"

    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert lotes[0]["cantidad_disponible"] == "8"
    assert lotes[1]["cantidad_disponible"] == "17"
    # El stock consolidado baja 5 unidades.
    existencias = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": base["almacen_id"], "q": producto["codigo"]},
        headers=base["admin"],
    ).json()
    assert existencias["items"][0]["cantidad_base"] == "25"


# --- Prueba 6: stock insuficiente en el lote --------------------------------
def test_6_no_se_puede_vender_mas_de_lo_que_tiene_el_lote(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])
    respuesta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": base["almacen_id"],
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "11",
                    "lote_id": lotes[0]["id"],
                }
            ],
        },
        headers=base["vendedor"],
    )
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["error"]["codigo"] == "stock_insuficiente"
    # El lote no se movió.
    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert lotes[0]["cantidad_disponible"] == "10"


# --- Prueba 7: ajuste manual sobre un lote ---------------------------------
def test_7_el_ajuste_manual_solo_toca_el_lote_elegido(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])
    ajuste = cliente.post(
        "/api/v1/inventario/ajustes",
        json={
            "almacen_id": base["almacen_id"],
            "producto_id": producto["id"],
            "lote_id": lotes[1]["id"],
            "cantidad_base": "-5",
            "motivo": "Rotura durante el manipuleo",
        },
        headers=base["admin"],
    )
    assert ajuste.status_code == 201, ajuste.text

    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert lotes[0]["cantidad_disponible"] == "10"
    assert lotes[1]["cantidad_disponible"] == "15"

    existencias = cliente.get(
        "/api/v1/inventario/existencias",
        params={"almacen_id": base["almacen_id"], "q": producto["codigo"]},
        headers=base["admin"],
    ).json()
    assert existencias["items"][0]["cantidad_base"] == "25"


# --- Prueba 8: cambio de precio de un lote ---------------------------------
def test_8_cambiar_el_precio_de_un_lote_no_toca_los_demas(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])

    # Primero se vende con el precio del lote viejo.
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": base["almacen_id"],
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "1",
                    "lote_id": lotes[0]["id"],
                }
            ],
        },
        headers=base["vendedor"],
    ).json()

    cambio = cliente.patch(
        f"/api/v1/lotes/{lotes[1]['id']}/precios",
        json={"presentacion_id": presentacion["id"], "precio": "13.50"},
        headers=base["admin"],
    )
    assert cambio.status_code == 200, cambio.text

    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert lotes[0]["precio_venta"] == "12"
    assert lotes[1]["precio_venta"] == "13.5"

    # La venta anterior no cambia.
    detalle = cliente.get(f"/api/v1/ventas/{venta['id']}", headers=base["admin"]).json()
    assert detalle["detalles"][0]["precio_unitario"] == "12"


# --- Prueba 9: anulación de una venta con dos lotes -----------------------
def test_9_la_anulacion_revierte_los_lotes(base, cliente):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    lotes = _lotes(cliente, base["admin"], producto["id"])
    venta = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": base["almacen_id"],
            "lineas": [
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "2",
                    "lote_id": lotes[0]["id"],
                },
                {
                    "producto_id": producto["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "3",
                    "lote_id": lotes[1]["id"],
                },
            ],
        },
        headers=base["vendedor"],
    ).json()

    anulacion = cliente.post(
        f"/api/v1/ventas/{venta['id']}/anular",
        json={"motivo": "Prueba de anulacion con dos lotes"},
        headers=base["admin"],
    )
    assert anulacion.status_code == 200, anulacion.text

    lotes = _lotes(cliente, base["admin"], producto["id"])
    assert lotes[0]["cantidad_disponible"] == "10"
    assert lotes[1]["cantidad_disponible"] == "20"


# --- Prueba 10: concurrencia sobre el ultimo lote --------------------------
def test_10_concurrencia_sobre_el_ultimo_lote(cliente, cabeceras_admin, unidades, almacen):
    """Dos ventas simultaneas de la ultima unidad: solo una se confirma."""
    from app.domain.unidades import ErrorStockInsuficiente
    from app.services import inventario as motor
    from app.services import ventas as servicio_ventas
    from app.tests.conftest import engine as motor_pruebas

    # Los hilos usan otras conexiones: los datos se confirman con una sesion propia.
    SesionPruebas = sessionmaker(bind=motor_pruebas, autoflush=False, autocommit=False)
    setup = SesionPruebas()
    setup.execute(text("SET lock_timeout = '8s'"))
    try:
        almacen_id = setup.execute(select(Almacen.id).order_by(Almacen.id).limit(1)).scalar_one_or_none()
        if almacen_id is None:
            almacen = Almacen(nombre="Almacen de prueba", activo=True, es_principal=True)
            setup.add(almacen)
            setup.flush()
            almacen_id = almacen.id

        unidad_id = setup.execute(select(UnidadMedida.id).limit(1)).scalar_one_or_none()
        if unidad_id is None:
            unidad = UnidadMedida(
                codigo="UND-CONC",
                nombre="Unidad prueba",
                dimension=Dimension.UNIDAD,
                paso_minimo=1,
                activo=True,
            )
            setup.add(unidad)
            setup.flush()
            unidad_id = unidad.id

        usuario_id = setup.execute(select(Usuario.id).limit(1)).scalar_one_or_none()
        if usuario_id is None:
            usuario = Usuario(
                nombre="Prueba concurrencia",
                usuario="prueba-concurrencia",
                password_hash="x",
                activo=True,
            )
            setup.add(usuario)
            setup.flush()
            usuario_id = usuario.id

        producto = Producto(
            codigo=f"CONC-{uuid.uuid4().hex[:6]}",
            nombre="Producto de concurrencia",
            nombre_normalizado="producto de concurrencia",
            unidad_base_id=unidad_id,
            stock_minimo_base=0,
            activo=True,
        )
        setup.add(producto)
        setup.flush()
        presentacion = PresentacionProducto(
            producto_id=producto.id,
            nombre="unidad",
            factor_base=1,
            precio_venta=12,
            activo=True,
        )
        setup.add(presentacion)
        setup.flush()

        lote = LoteInventario(
            producto_id=producto.id,
            codigo_lote=f"{producto.codigo}-L001",
            cantidad_inicial=1,
            cantidad_disponible=0,
            costo_base=8,
            costo_unitario=8,
            precio_venta=12,
            presentacion_principal_id=presentacion.id,
            almacen_id=almacen_id,
            estado="ACTIVO",
            origen="RECEPCION",
        )
        setup.add(lote)
        setup.flush()
        # El stock del lote entra con el movimiento (una sola via de entrada).
        motor.aplicar_entrada(
            setup,
            almacen_id=almacen_id,
            producto_id=producto.id,
            cantidad_base=1,
            costo_unitario_base=8,
            tipo="ABASTECIMIENTO",
            origen_tipo="PRUEBA",
            origen_id=0,
            usuario_id=usuario_id,
            referencia="PRUEBA",
            lote_id=lote.id,
        )
        setup.commit()
        producto_id = producto.id
        presentacion_id = presentacion.id
        lote_id = lote.id
    finally:
        setup.close()

    resultados: list[str] = []
    barrera = threading.Barrier(2)

    def vender() -> None:
        sesion = SesionPruebas()
        try:
            sesion.execute(text("SET lock_timeout = '8s'"))
            barrera.wait(timeout=30)
            servicio_ventas.confirmar(
                sesion,
                {
                    "almacen_id": almacen_id,
                    "lineas": [
                        {
                            "producto_id": producto_id,
                            "presentacion_id": presentacion_id,
                            "cantidad": "1",
                            "lote_id": lote_id,
                        }
                    ],
                },
                usuario_id,
            )
            sesion.commit()
            resultados.append("ok")
        except ErrorStockInsuficiente:
            sesion.rollback()
            resultados.append("sin_stock")
        except Exception as error:  # pragma: no cover - diagnostico
            sesion.rollback()
            resultados.append(f"error: {error}")
        finally:
            sesion.close()

    hilos = [threading.Thread(target=vender) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)

    assert not [r for r in resultados if r.startswith("error")], resultados
    assert resultados.count("ok") == 1, resultados
    assert resultados.count("sin_stock") == 1, resultados

    verificacion = SesionPruebas()
    try:
        lote = verificacion.execute(
            select(LoteInventario).where(LoteInventario.id == lote_id)
        ).scalar_one()
        assert Decimal(str(lote.cantidad_disponible)) == Decimal("0")

        # Limpieza: la prueba confirmo datos en la base de pruebas y no debe
        # affectar a las pruebas que se ejecuten despues.
        verificacion.execute(
            text("DELETE FROM movimientos_inventario WHERE producto_id = :p"),
            {"p": producto_id},
        )
        verificacion.execute(
            text(
                "DELETE FROM ventas WHERE id IN "
                "(SELECT venta_id FROM detalle_ventas WHERE producto_id = :p)"
            ),
            {"p": producto_id},
        )
        verificacion.execute(
            text("DELETE FROM detalle_ventas WHERE producto_id = :p"), {"p": producto_id}
        )
        verificacion.execute(
            text("DELETE FROM existencias WHERE producto_id = :p"), {"p": producto_id}
        )
        verificacion.execute(
            text("DELETE FROM lotes_inventario WHERE producto_id = :p"), {"p": producto_id}
        )
        verificacion.execute(
            text("DELETE FROM productos WHERE id = :p"), {"p": producto_id}
        )
        verificacion.commit()
    finally:
        verificacion.close()


# --- Prueba 11: productos sin lotes siguen funcionando ----------------------
def test_11_un_producto_sin_lotes_conserva_el_comportamiento_anterior(
    cliente, cabeceras_admin, unidades, almacen, db
):
    """El camino sin lotes (producto historico) se comporta igual que antes."""
    from app.services import inventario as motor

    producto = _producto(cliente, cabeceras_admin, unidades, codigo="SIN-LOTES")
    presentacion = producto["presentaciones"][0]
    # Entrada directa al motor, sin lote (como el sistema anterior).
    motor.aplicar_entrada(
        db,
        almacen_id=almacen.id,
        producto_id=producto["id"],
        cantidad_base=Decimal("5"),
        costo_unitario_base=Decimal("8"),
        tipo="ABASTECIMIENTO",
        origen_tipo="PRUEBA",
        origen_id=0,
        usuario_id=None,
        referencia="PRUEBA",
    )
    db.commit()

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
        headers=cabeceras_admin,
    )
    assert venta.status_code == 201, venta.text
    # El precio es el de la presentacion (no hay lote).
    assert venta.json()["detalles"][0]["precio_unitario"] == "12"
    assert venta.json()["detalles"][0]["lote_id"] is None


# --- Prueba 12: codigo de barras con varios lotes --------------------------
def test_12_el_codigo_de_barras_ofrece_los_lotes_del_producto(base, cliente, unidades):
    producto = base["producto"]
    presentacion = base["presentacion"]
    _ingreso(
        cliente,
        base["admin"],
        base["proveedor"]["id"],
        base["almacen_id"],
        producto,
        presentacion,
        "20",
        "9.50",
        "14.00",
    )
    # El codigo de barras del producto identifica el producto, no el lote.
    producto_con_barras = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": f"LOT-BAR-{uuid.uuid4().hex[:6]}",
            "nombre": "Producto con codigo de barras",
            "unidad_base_id": unidades["UND"].id,
            "presentaciones": [
                {
                    "nombre": "unidad",
                    "factor_base": "1",
                    "precio_venta": "5.00",
                    "codigo_barras": f"77512345{uuid.uuid4().hex[:4]}",
                }
            ],
        },
        headers=base["admin"],
    ).json()
    assert producto_con_barras["presentaciones"][0]["codigo_barras"].startswith("77512345")

    # La ficha del producto ofrece los lotes con su precio.
    ficha = cliente.get(
        f"/api/v1/inventario/productos/{producto['id']}/ficha", headers=base["admin"]
    ).json()
    assert len(ficha["lotes"]) == 2
    assert ficha["lotes"][0]["precio_venta"] == "12"
    assert ficha["lotes"][1]["precio_venta"] == "14"


# --- Prueba 13: compatibilidad con las pruebas existentes -------------------
def test_13_las_existencias_consolidadas_siguen_coincidiendo_con_los_lotes(
    cliente, cabeceras_admin, unidades, almacen, db
):
    """La suma de los lotes debe coincidir con la existencia consolidada."""
    from app.db.models import Existencia

    producto = _producto(cliente, cabeceras_admin, unidades, codigo="LOT-CONCILIACION")
    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-CONC", "razon_social": "Distribuidora SAC"},
        headers=cabeceras_admin,
    ).json()
    presentacion = producto["presentaciones"][0]
    for cantidad, costo in (("10", "8.00"), ("20", "9.50")):
        _ingreso(
            cliente,
            cabeceras_admin,
            proveedor["id"],
            almacen.id,
            producto,
            presentacion,
            cantidad,
            costo,
        )

    lotes = _lotes(cliente, cabeceras_admin, producto["id"])
    suma_lotes = sum(Decimal(lote["cantidad_disponible"]) for lote in lotes)
    existencia = db.execute(
        select(Existencia).where(
            Existencia.producto_id == producto["id"],
            Existencia.almacen_id == almacen.id,
        )
    ).scalar_one()
    assert Decimal(str(existencia.cantidad_base)) == suma_lotes


# --- Prueba 14: venta de medios sacos (-1/2 y luego -1 saco) y transporte ---
def test_14_venta_de_dos_medios_sacos_y_costo_con_transporte(
    cliente, cabeceras_admin, cabeceras_vendedor, unidades, almacen
):
    """Vender medio saco resta 1/2 saco al lote; otro medio saco completa 1 saco."""
    balanceado = cliente.post(
        "/api/v1/catalogo/productos",
        json={
            "codigo": "BAL-40KG",
            "nombre": "Vitamaxpro Terneros Cuna",
            "unidad_base_id": unidades["GR"].id,
            "permite_fraccion": True,
            "presentaciones": [
                {
                    "nombre": "saco 40 kg pellet",
                    "factor_base": "40000",
                    "precio_venta": "120.00",
                    "permite_fraccion": True,
                }
            ],
        },
        headers=cabeceras_admin,
    ).json()
    presentacion = balanceado["presentaciones"][0]
    proveedor = cliente.post(
        "/api/v1/proveedores",
        json={"codigo": "PRV-BAL", "razon_social": "Vitamaxpro"},
        headers=cabeceras_admin,
    ).json()

    # Ingreso de 10 sacos a S/ 80.00 + S/ 50.00 de transporte = S/ 850.00 total
    # (Costo real por saco = S/ 85.00; costo por gramo = 85 / 40000 = 0.002125)
    ingreso = cliente.post(
        "/api/v1/abastecimientos",
        json={
            "proveedor_id": proveedor["id"],
            "almacen_id": almacen.id,
            "documento": "F001-TRANSP",
            "lineas": [
                {
                    "producto_id": balanceado["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "10",
                    "costo_unitario": "80.00",
                    "costo_transporte": "50.00",
                    "precio_venta": "120.00",
                }
            ],
        },
        headers=cabeceras_admin,
    )
    assert ingreso.status_code == 201, ingreso.text
    datos_ingreso = ingreso.json()
    assert datos_ingreso["total"] == "850"
    assert datos_ingreso["detalles"][0]["costo_transporte"] == "50"
    assert datos_ingreso["detalles"][0]["subtotal"] == "850"

    lotes = _lotes(cliente, cabeceras_admin, balanceado["id"])
    assert len(lotes) == 1
    lote_id = lotes[0]["id"]
    assert lotes[0]["cantidad_disponible"] == "400000"
    assert lotes[0]["cantidad_disponible_presentacion"] == "10"
    assert lotes[0]["costo_transporte"] == "50"
    assert lotes[0]["costo_base"] == "0.002125"

    # 1. Primera venta de medio saco (0.5): debe restar 1/2 saco -> quedan 9.5 sacos (380 000 g)
    venta_1 = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": balanceado["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "0.5",
                    "lote_id": lote_id,
                }
            ],
        },
        headers=cabeceras_vendedor,
    )
    assert venta_1.status_code == 201, venta_1.text
    assert venta_1.json()["total"] == "60"
    # Costo de medio saco con transporte incluido: 20 000 g * 0.002125 = S/ 42.50
    assert venta_1.json()["costo_total"] == "42.5"

    lotes = _lotes(cliente, cabeceras_admin, balanceado["id"])
    assert lotes[0]["cantidad_disponible"] == "380000"
    assert lotes[0]["cantidad_disponible_presentacion"] == "9.5"

    # 2. Segunda venta de medio saco (0.5): completa 1 saco vendido -> quedan 9 sacos (360 000 g)
    venta_2 = cliente.post(
        "/api/v1/ventas",
        json={
            "almacen_id": almacen.id,
            "lineas": [
                {
                    "producto_id": balanceado["id"],
                    "presentacion_id": presentacion["id"],
                    "cantidad": "0.5",
                    "lote_id": lote_id,
                }
            ],
        },
        headers=cabeceras_vendedor,
    )
    assert venta_2.status_code == 201, venta_2.text
    lotes = _lotes(cliente, cabeceras_admin, balanceado["id"])
    assert lotes[0]["cantidad_disponible"] == "360000"
    assert lotes[0]["cantidad_disponible_presentacion"] == "9"
