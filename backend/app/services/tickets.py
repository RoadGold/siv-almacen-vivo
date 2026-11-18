"""Armado del ticket de venta (texto listo para la impresora ESC/POS).

El ticket es **interno**: sirve para el control del día y para el cliente, pero
no sustituye a los comprobantes tributarios exigibles.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.domain.pagos import ETIQUETAS_FORMA_PAGO
from app.domain.unidades import dec, q2
from app.services import configuracion
from app.services.impresora import ConstructorTicket, enviar


def _dinero(valor: Decimal | str | None) -> str:
    if valor is None:
        return ""
    return f"S/ {q2(dec(valor)):,.2f}".replace(",", " ").replace(".", ",")


def _cantidad(valor: Decimal | str | None) -> str:
    """Cantidad sin ceros sobrantes: 4.0000 -> 4 · 0.7500 -> 0.75."""
    if valor is None:
        return ""
    texto = f"{dec(valor):f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto or "0"


def _truncar(texto: str, largo: int) -> str:
    if len(texto) <= largo:
        return texto
    return texto[: max(1, largo - 1)] + "…"


def _fecha_hora(fecha: Any) -> str:
    if isinstance(fecha, datetime):
        return fecha.strftime("%d/%m/%Y %H:%M")
    if hasattr(fecha, "strftime"):
        return fecha.strftime("%d/%m/%Y")
    return str(fecha)


def construir_ticket(
    db,
    venta: Any,
    *,
    configuracion_impresora=None,
    base_url: str = "",
) -> bytes:
    """Construye los bytes ESC/POS del ticket de una venta."""
    from app.services.impresora import ConfigImpresora

    config = configuracion_impresora or ConfigImpresora.desde_configuracion()
    datos = configuracion.obtener_todo(db)
    mostrar_original = configuracion.boolean(db, "ticket_mostrar_precio_original")
    mostrar_qr = configuracion.boolean(db, "ticket_mostrar_qr")

    t = ConstructorTicket(config).reiniciar().tabla_caracteres()

    # --- Encabezado del negocio -------------------------------------------
    nombre = datos.get("negocio_nombre") or "SIV · Almacén Vivo"
    t.centro(nombre.upper()).doble(False)
    if datos.get("negocio_ruc"):
        t.centro(f"RUC {datos['negocio_ruc']}")
    if datos.get("negocio_direccion"):
        t.centro(datos["negocio_direccion"])
    if datos.get("negocio_telefono"):
        t.centro(f"Tel. {datos['negocio_telefono']}")
    t.separador()

    # --- Identificación del ticket ----------------------------------------
    t.centro("TICKET INTERNO DE VENTA").doble(False)
    t.pares("Ticket", venta.numero)
    t.pares("Fecha", _fecha_hora(venta.fecha))
    t.pares("Cajero", venta.usuario.nombre if venta.usuario else "-")
    t.separador()

    # --- Detalle ----------------------------------------------------------
    for detalle in venta.detalles:
        producto = detalle.producto
        presentacion = detalle.presentacion
        nombre_producto = producto.nombre if producto else "Producto"
        nombre_presentacion = presentacion.nombre if presentacion else ""
        descripcion = f"{nombre_producto} ({nombre_presentacion})" if nombre_presentacion else nombre_producto

        cantidad = _cantidad(detalle.cantidad)
        precio = dec(detalle.precio_unitario)
        subtotal = dec(detalle.subtotal)

        t.linea(f"{_truncar(descripcion, t.columnas - 1)}")
        t.pares(f"  {cantidad} x {_dinero(precio)}", _dinero(subtotal))

        original = (
            dec(detalle.precio_original)
            if detalle.precio_original is not None
            else None
        )
        if mostrar_original and original is not None and original != precio:
            t.derecha(f"(precio de lista {_dinero(original)})")
            if detalle.motivo_precio:
                t.derecha(f"motivo: {detalle.motivo_precio}")

    t.separador()

    # --- Totales y pago ---------------------------------------------------
    t.pares("TOTAL", _dinero(venta.total))
    if venta.forma_pago:
        t.pares("Pago", ETIQUETAS_FORMA_PAGO.get(str(venta.forma_pago), str(venta.forma_pago).capitalize()))
    if venta.monto_recibido is not None:
        t.pares("Recibido", _dinero(venta.monto_recibido))
    if venta.vuelto is not None:
        t.pares("Vuelto", _dinero(venta.vuelto))
    if venta.deuda is not None:
        t.pares("DEUDA", _dinero(venta.deuda))
    t.separador()

    # --- Código QR y pie ---------------------------------------------------
    if mostrar_qr:
        contenido = venta.numero
        if base_url:
            contenido = f"{base_url}/ventas/{venta.id}"
        t.centro("[ QR ]")
        t.codigo_qr(contenido)

    pie = datos.get("ticket_pie") or "¡Gracias por su compra!"
    t.centro(pie).doble(False)
    t.avanzar(2).cortar()

    return t.bytes()


def contenido_texto_ticket(db, venta: Any) -> str:
    """Versión en texto del ticket (para pruebas y para ver el resultado sin imprimir)."""
    from app.services.impresora import ConfigImpresora

    config = ConfigImpresora.desde_configuracion()
    datos = configuracion.obtener_todo(db)
    lineas: list[str] = []
    lineas.append(datos.get("negocio_nombre", "").upper())
    if datos.get("negocio_ruc"):
        lineas.append(f"RUC {datos['negocio_ruc']}")
    if datos.get("negocio_direccion"):
        lineas.append(datos["negocio_direccion"])
    lineas.append("-" * config.columnas)
    lineas.append("TICKET INTERNO DE VENTA")
    lineas.append(f"Ticket {venta.numero}   {_fecha_hora(venta.fecha)}")
    lineas.append(f"Cajero {venta.usuario.nombre if venta.usuario else '-'}")
    lineas.append("-" * config.columnas)
    for detalle in venta.detalles:
        producto = detalle.producto
        presentacion = detalle.presentacion
        nombre = producto.nombre if producto else "Producto"
        nombre_p = presentacion.nombre if presentacion else ""
        lineas.append(f"{nombre} ({nombre_p})" if nombre_p else nombre)
        lineas.append(
            f"  {_cantidad(detalle.cantidad)} x {_dinero(detalle.precio_unitario)}"
            f"   {_dinero(detalle.subtotal)}"
        )
        original = (
            dec(detalle.precio_original)
            if detalle.precio_original is not None
            else None
        )
        if original is not None and original != dec(detalle.precio_unitario):
            lineas.append(f"    (precio de lista {_dinero(original)})")
            if detalle.motivo_precio:
                lineas.append(f"    motivo: {detalle.motivo_precio}")
    lineas.append("-" * config.columnas)
    lineas.append(f"TOTAL {_dinero(venta.total)}")
    if venta.forma_pago:
        lineas.append(f"Pago {ETIQUETAS_FORMA_PAGO.get(str(venta.forma_pago), str(venta.forma_pago))}")
    if venta.monto_recibido is not None:
        lineas.append(f"Recibido {_dinero(venta.monto_recibido)}")
    if venta.vuelto is not None:
        lineas.append(f"Vuelto {_dinero(venta.vuelto)}")
    if venta.deuda is not None:
        lineas.append(f"DEUDA {_dinero(venta.deuda)}")
    lineas.append("-" * config.columnas)
    lineas.append(datos.get("ticket_pie", "¡Gracias por su compra!"))
    return "\n".join(lineas)


def imprimir_venta(
    db,
    venta_id: int,
    usuario_id: int | None = None,
    *,
    reimpresion: bool = False,
) -> dict:
    """Imprime (o reimprime) el ticket de una venta y deja constancia del intento.

    La venta nunca se pierde si la impresión falla: queda registrada con el
    error para poder reintentarla desde el historial de ventas.
    """
    import time

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.models import DetalleVenta, ImpresionVenta, Venta
    from app.domain.unidades import ErrorNegocio
    from app.services import auditoria
    from app.services.impresora import ConfigImpresora, ErrorImpresora

    venta = db.execute(
        select(Venta)
        .options(
            selectinload(Venta.detalles).selectinload(DetalleVenta.producto),
            selectinload(Venta.detalles).selectinload(DetalleVenta.presentacion),
            selectinload(Venta.usuario),
        )
        .where(Venta.id == venta_id)
    ).scalar_one_or_none()
    if venta is None:
        raise ErrorNegocio("La venta no existe.", detalle={"venta_id": venta_id})
    if venta.estado != "CONFIRMADO":
        raise ErrorNegocio(
            "Solo se puede imprimir el ticket de una venta confirmada.",
            detalle={"estado": venta.estado.value},
        )

    config = ConfigImpresora.desde_configuracion()
    inicio = time.perf_counter()
    try:
        datos = construir_ticket(db, venta, configuracion_impresora=config)
        enviar(datos, config)
    except ErrorImpresora as error:
        duracion = int((time.perf_counter() - inicio) * 1000)
        venta.ticket_impreso = False
        venta.impresion_error = error.mensaje
        db.add(
            ImpresionVenta(
                venta_id=venta.id,
                resultado="ERROR",
                mensaje=error.mensaje,
                reimpresion=reimpresion,
                usuario_id=usuario_id,
                duracion_ms=duracion,
            )
        )
        db.flush()
        raise

    duracion = int((time.perf_counter() - inicio) * 1000)
    venta.ticket_impreso = True
    venta.impreso_at = datetime.now().astimezone()
    venta.impresion_error = None
    db.add(
        ImpresionVenta(
            venta_id=venta.id,
            resultado="OK",
            mensaje="Ticket impreso.",
            reimpresion=reimpresion,
            usuario_id=usuario_id,
            duracion_ms=duracion,
        )
    )
    auditoria.registrar(
        db,
        accion="venta.ticket_imprimir",
        entidad="venta",
        entidad_id=venta.id,
        actor_id=usuario_id,
        detalle={"numero": venta.numero, "reimpresion": reimpresion},
    )
    db.flush()
    return {
        "ok": True,
        "mensaje": "Ticket impreso.",
        "numero": venta.numero,
        "duracion_ms": duracion,
        "reimpresion": reimpresion,
    }


__all__ = ["construir_ticket", "contenido_texto_ticket", "imprimir_venta"]
