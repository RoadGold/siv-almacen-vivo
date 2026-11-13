"""Endpoints de la impresora de tickets."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.domain.unidades import ErrorNegocio
from app.services import configuracion as servicio_configuracion
from app.services import tickets as servicio_tickets
from app.services.impresora import (
    ConfigImpresora,
    ConstructorTicket,
    ErrorImpresora,
    comprobar,
    enviar,
)

router = APIRouter(prefix="/impresora", tags=["Impresora"])


@router.get("/estado")
def estado(
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
) -> dict:
    """Estado de la impresora: configuración y si responde."""
    config = ConfigImpresora.desde_configuracion()
    conexion = comprobar(config)
    return {
        "activa": config.activa,
        "host": config.host,
        "puerto": config.puerto,
        "columnas": config.columnas,
        "cortar": config.cortar,
        "qr": config.qr,
        "pagina_codigo": config.pagina_codigo,
        "conectada": conexion["conectada"],
        "mensaje": conexion["mensaje"],
    }


@router.post("/prueba")
def prueba(
    _: Usuario = Depends(requiere_permiso(Permiso.ADMIN_USUARIOS)),
    db: Session = Depends(get_db),
) -> dict:
    """Imprime un ticket de prueba."""
    config = ConfigImpresora.desde_configuracion()
    if not config.activa:
        raise ErrorImpresora(
            "La impresora está desactivada. Actívela en la configuración del sistema."
        )
    datos = servicio_configuracion.obtener_todo(db)
    t = ConstructorTicket(config).reiniciar().tabla_caracteres()
    t.centro("SIV · ALMACÉN VIVO").doble(False)
    t.centro("TICKET DE PRUEBA")
    t.centro(datos.get("negocio_nombre", "").upper())
    if datos.get("negocio_ruc"):
        t.centro(f"RUC {datos['negocio_ruc']}")
    t.separador()
    t.centro("Si puede leer esto,")
    t.centro("la impresora está bien configurada.")
    t.separador()
    t.centro("Acentos: áéíóúñ ¿ ¡")
    t.centro("Precios: S/ 1 234,56")
    t.codigo_qr("SIV-PRUEBA")
    t.avanzar(2).cortar()
    try:
        enviar(t.bytes(), config)
    except ErrorImpresora:
        raise
    return {"ok": True, "mensaje": "Ticket de prueba enviado a la impresora."}


@router.get("/ticket/{venta_id}")
def ver_ticket(
    venta_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.VENTAS_VER)),
    db: Session = Depends(get_db),
) -> dict:
    """Vista en texto del ticket de una venta (sin imprimir)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.models import DetalleVenta, Venta

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
    return {"texto": servicio_tickets.contenido_texto_ticket(db, venta)}
