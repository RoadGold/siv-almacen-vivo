"""Configuración del negocio y de la caja (tabla `configuracion`).

Guarda los datos que aparecen en el ticket (nombre comercial, RUC, dirección,
teléfono, mensaje final) y las reglas de la caja (límite de descuento,
formato del ticket).

El contenido se guarda como texto en la tabla `configuracion` (clave/valor),
de modo que el administrador pueda cambiarlo sin tocar la base a mano.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Configuracion
from app.domain.unidades import dec

# --- Claves y valores por defecto ------------------------------------------
CLAVES = {
    "negocio_nombre": "",
    "negocio_ruc": "",
    "negocio_direccion": "",
    "negocio_telefono": "",
    "ticket_pie": "¡Gracias por su compra!",
    "ticket_mostrar_precio_original": "si",
    "ticket_mostrar_qr": "si",
    "ticket_ancho": "80",
    "venta_descuento_maximo_porcentaje": "20",
    "venta_descuento_maximo_monto": "0",
}

# Valores que solo pueden ser de una lista cerrada.
VALORES_CERRADOS = {
    "ticket_mostrar_precio_original": {"si", "no"},
    "ticket_mostrar_qr": {"si", "no"},
    "ticket_ancho": {"58", "80"},
}

DESCRIPCIONES = {
    "negocio_nombre": "Nombre comercial que aparece en el ticket",
    "negocio_ruc": "RUC del negocio",
    "negocio_direccion": "Dirección del negocio",
    "negocio_telefono": "Teléfono de contacto",
    "ticket_pie": "Mensaje final del ticket",
    "ticket_mostrar_precio_original": "Mostrar el precio de lista cuando cambió (si/no)",
    "ticket_mostrar_qr": "Incluir código QR en el ticket (si/no)",
    "ticket_ancho": "Ancho del papel: 58 o 80 mm",
    "venta_descuento_maximo_porcentaje": "Descuento máximo que puede aplicar el vendedor (%)",
    "venta_descuento_maximo_monto": "Descuento máximo en soles (0 = sin tope)",
}


def obtener_todo(db: Session) -> dict[str, str]:
    """Devuelve la configuración completa con los valores por defecto."""
    valores = dict(CLAVES)
    for fila in db.execute(select(Configuracion)).scalars().all():
        if fila.clave in valores:
            valores[fila.clave] = fila.valor or ""
    if not valores["negocio_nombre"]:
        valores["negocio_nombre"] = settings.nombre_negocio
    return valores


def valor(db: Session, clave: str, defecto: str = "") -> str:
    fila = db.get(Configuracion, clave)
    if fila is None or fila.valor is None:
        return CLAVES.get(clave, defecto) or defecto
    return fila.valor


def boolean(db: Session, clave: str) -> bool:
    return valor(db, clave).strip().lower() in {"si", "sí", "true", "1", "x"}


def decimal(db: Session, clave: str, defecto: str = "0") -> Decimal:
    bruto = valor(db, clave) or defecto
    try:
        return dec(bruto)
    except Exception:
        return dec(defecto)


def guardar(db: Session, datos: dict[str, Any], usuario_id: int | None = None) -> dict[str, str]:
    """Guarda la configuración y deja constancia en la auditoría."""
    from app.services import auditoria

    cambios: dict[str, str] = {}
    for clave, valor_nuevo in (datos or {}).items():
        if clave not in CLAVES:
            continue
        texto = str(valor_nuevo).strip() if valor_nuevo is not None else ""
        if clave in VALORES_CERRADOS and texto.lower() not in VALORES_CERRADOS[clave]:
            permitidos = ", ".join(sorted(VALORES_CERRADOS[clave]))
            raise ValueError(f"El valor de «{clave}» debe ser uno de: {permitidos}.")
        if clave in {"venta_descuento_maximo_porcentaje", "venta_descuento_maximo_monto"}:
            try:
                if dec(texto) < 0:
                    raise ValueError("El límite no puede ser negativo.")
            except Exception as exc:
                raise ValueError(f"El valor de «{clave}» no es un número válido.") from exc
        actual = db.get(Configuracion, clave)
        if actual is None:
            db.add(Configuracion(clave=clave, valor=texto))
        else:
            actual.valor = texto
        cambios[clave] = texto
    db.flush()

    if cambios:
        auditoria.registrar(
            db,
            accion="configuracion.actualizar",
            entidad="configuracion",
            entidad_id=None,
            actor_id=usuario_id,
            detalle={"claves": sorted(cambios.keys())},
        )
    return obtener_todo(db)


def descripciones() -> dict[str, str]:
    return dict(DESCRIPCIONES)


__all__ = [
    "CLAVES",
    "DESCRIPCIONES",
    "boolean",
    "decimal",
    "descripciones",
    "guardar",
    "obtener_todo",
    "valor",
]
