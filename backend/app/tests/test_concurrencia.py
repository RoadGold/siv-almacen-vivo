"""Pruebas de concurrencia (plan Â§11.1 Â· T09) y de atomicidad (T11)."""

from __future__ import annotations

import threading
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Almacen,
    Dimension,
    PresentacionProducto,
    Producto,
    Rol,
    RolNombre,
    UnidadMedida,
    Usuario,
    UsuarioRol,
)
from app.db.session import SessionLocal
from app.domain.unidades import ErrorStockInsuficiente
from app.services import ventas as servicio_ventas
from app.tests.conftest import engine as motor_pruebas

# La prueba usa la base de datos de pruebas (tmpfs), nunca la de desarrollo.
SesionPruebas = sessionmaker(bind=motor_pruebas, autoflush=False, autocommit=False, future=True)


def _preparar_datos() -> dict:
    """Crea datos reales (confirmados) para la prueba de concurrencia."""
    db = SesionPruebas()
    try:
        unidad = db.execute(
            select(UnidadMedida).where(UnidadMedida.codigo == "UND")
        ).scalar_one_or_none()
        if unidad is None:
            unidad = UnidadMedida(
                codigo="UND", nombre="Unidad", dimension=Dimension.UNIDAD, paso_minimo=1
            )
            db.add(unidad)
            db.flush()

        almacen = db.execute(
            select(Almacen).where(Almacen.es_principal.is_(True))
        ).scalar_one_or_none()
        if almacen is None:
            almacen = Almacen(nombre="AlmacÃ©n principal", activo=True, es_principal=True)
            db.add(almacen)
            db.flush()

        rol = db.execute(select(Rol).where(Rol.nombre == RolNombre.ADMINISTRADOR.value)).scalar_one_or_none()
        if rol is None:
            rol = Rol(nombre=RolNombre.ADMINISTRADOR.value)
            db.add(rol)
            db.flush()

        usuario = db.execute(select(Usuario).where(Usuario.usuario == "concurrencia")).scalar_one_or_none()
        if usuario is None:
            usuario = Usuario(
                nombre="Concurrencia",
                usuario="concurrencia",
                password_hash="x",
                activo=True,
            )
            db.add(usuario)
            db.flush()
            db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))
            db.flush()

        codigo = f"CONC-{uuid.uuid4().hex[:8]}"
        producto = Producto(
            codigo=codigo,
            nombre="Producto de prueba concurrency",
            nombre_normalizado="producto de prueba concurrency",
            unidad_base_id=unidad.id,
            stock_minimo_base=0,
            activo=True,
        )
        db.add(producto)
        db.flush()
        presentacion = PresentacionProducto(
            producto_id=producto.id,
            nombre="unidad",
            factor_base=Decimal("1"),
            precio_venta=Decimal("10.00"),
            activo=True,
        )
        db.add(presentacion)
        db.flush()
        db.commit()
        return {
            "producto_id": producto.id,
            "presentacion_id": presentacion.id,
            "almacen_id": almacen.id,
            "usuario_id": usuario.id,
        }
    finally:
        db.close()


def _vender_una_unidad(datos: dict, barrera: threading.Barrier, resultado: list) -> None:
    db = SesionPruebas()
    try:
        barrera.wait(timeout=30)
        payload = {
            "almacen_id": datos["almacen_id"],
            "lineas": [
                {
                    "producto_id": datos["producto_id"],
                    "presentacion_id": datos["presentacion_id"],
                    "cantidad": "1",
                }
            ],
        }
        venta = servicio_ventas.confirmar(db, payload, datos["usuario_id"])
        db.commit()
        resultado.append(("ok", venta.numero))
    except ErrorStockInsuficiente:
        db.rollback()
        resultado.append(("sin_stock", None))
    except Exception as exc:  # pragma: no cover - diagnÃ³stico
        db.rollback()
        resultado.append(("error", str(exc)))
    finally:
        db.close()


def test_t09_dos_vendedores_disputan_la_ultima_unidad():
    datos = _preparar_datos()

    # Se deja exactamente una unidad en stock.
    db = SesionPruebas()
    try:
        from app.services import inventario

        inventario.aplicar_entrada(
            db,
            almacen_id=datos["almacen_id"],
            producto_id=datos["producto_id"],
            cantidad_base=Decimal("1"),
            costo_unitario_base=Decimal("5"),
            tipo="ABASTECIMIENTO",
            origen_tipo="PRUEBA",
            origen_id=0,
            usuario_id=datos["usuario_id"],
            referencia="PRUEBA",
        )
        db.commit()
    finally:
        db.close()

    barrera = threading.Barrier(2)
    resultado: list = []
    hilos = [
        threading.Thread(target=_vender_una_unidad, args=(datos, barrera, resultado)),
        threading.Thread(target=_vender_una_unidad, args=(datos, barrera, resultado)),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)

    exitosas = [r for r in resultado if r[0] == "ok"]
    sin_stock = [r for r in resultado if r[0] == "sin_stock"]
    errores = [r for r in resultado if r[0] == "error"]

    assert not errores, f"Errores inesperados: {errores}"
    assert len(exitosas) == 1, f"Debe existir exactamente una venta vÃ¡lida: {resultado}"
    assert len(sin_stock) == 1, f"La segunda venta debe rechazarse por stock: {resultado}"

    # El stock no puede quedar negativo.
    db = SesionPruebas()
    try:
        from app.services import inventario

        saldo = inventario.existencia_actual(db, datos["almacen_id"], datos["producto_id"])
        assert saldo is not None
        assert Decimal(str(saldo.cantidad_base)) == Decimal("0")
    finally:
        db.close()


def test_t11_transaccion_se_revierte_si_falla_un_movimiento(monkeypatch):
    """Si el movimiento de inventario falla, la venta completa se revierte."""
    datos = _preparar_datos()

    db = SesionPruebas()
    try:
        from app.services import inventario

        inventario.aplicar_entrada(
            db,
            almacen_id=datos["almacen_id"],
            producto_id=datos["producto_id"],
            cantidad_base=Decimal("10"),
            costo_unitario_base=Decimal("5"),
            tipo="ABASTECIMIENTO",
            origen_tipo="PRUEBA",
            origen_id=0,
            usuario_id=datos["usuario_id"],
            referencia="PRUEBA",
        )
        db.commit()
    finally:
        db.close()

    original = inventario.registrar_movimiento

    def _fallar(*args, **kwargs):
        raise RuntimeError("fallo simulado al registrar el movimiento")

    monkeypatch.setattr(inventario, "registrar_movimiento", _fallar)
    # ventas.py llama al sÃ­mbolo imported en su propio mÃ³dulo
    import app.services.ventas as modulo_ventas

    monkeypatch.setattr(modulo_ventas.inventario, "registrar_movimiento", _fallar)

    db = SesionPruebas()
    try:
        payload = {
            "almacen_id": datos["almacen_id"],
            "lineas": [
                {
                    "producto_id": datos["producto_id"],
                    "presentacion_id": datos["presentacion_id"],
                    "cantidad": "2",
                }
            ],
        }
        with pytest.raises(RuntimeError):
            servicio_ventas.confirmar(db, payload, datos["usuario_id"])
        db.rollback()
    finally:
        db.close()

    monkeypatch.setattr(inventario, "registrar_movimiento", original)

    # La venta no quedÃ³ registrada ni descontada.
    db = SesionPruebas()
    try:
        from app.db.models import DetalleVenta, Venta
        from app.services import inventario

        ventas = db.execute(
            select(Venta)
            .join(DetalleVenta, DetalleVenta.venta_id == Venta.id)
            .where(
                Venta.almacen_id == datos["almacen_id"],
                DetalleVenta.producto_id == datos["producto_id"],
            )
        ).scalars().all()
        assert len(ventas) == 0
        existencia = inventario.existencia_actual(db, datos["almacen_id"], datos["producto_id"])
        assert Decimal(str(existencia.cantidad_base)) == Decimal("10")
    finally:
        db.close()

