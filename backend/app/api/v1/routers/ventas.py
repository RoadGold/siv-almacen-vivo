"""Endpoints de ventas (punto de venta)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, permisos_usuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.models import DetalleVenta, Usuario, Venta
from app.db.session import get_db
from app.schemas.common import Pagina
from app.schemas.ventas import (
    AnulacionVentaIn,
    PrevisualizacionVentaOut,
    VentaIn,
    VentaOut,
)
from app.services import auditoria
from app.services import ventas as servicio

router = APIRouter(prefix="/ventas", tags=["Ventas"])


@router.post("/previsualizar", response_model=PrevisualizacionVentaOut)
def previsualizar(
    datos: VentaIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.VENTAS_CREAR)),
    db: Session = Depends(get_db),
) -> PrevisualizacionVentaOut:
    return PrevisualizacionVentaOut(
        **servicio.previsualizar(
            db,
            datos.model_dump(),
            puede_cambiar_precio=_puede_cambiar_precio(usuario),
        )
    )


def _puede_cambiar_precio(usuario: Usuario) -> bool:
    """Solo quien administra precios puede fijar un precio distinto al de la presentación."""
    return Permiso.PRECIOS_GESTIONAR.value in permisos_usuario(usuario)


@router.post("", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
def confirmar(
    datos: VentaIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.VENTAS_CREAR)),
    db: Session = Depends(get_db),
) -> VentaOut:
    venta = servicio.confirmar(
        db,
        datos.model_dump(),
        usuario.id,
        puede_cambiar_precio=_puede_cambiar_precio(usuario),
    )
    auditoria.registrar(
        db,
        accion="venta.confirmar",
        entidad="venta",
        entidad_id=venta.id,
        actor_id=usuario.id,
        detalle={"numero": venta.numero, "total": str(venta.total)},
    )
    db.commit()
    db.refresh(venta)
    venta = _cargar(db, venta.id)
    return VentaOut(**servicio.venta_a_dict(venta))


def _cargar(db: Session, venta_id: int) -> Venta:
    venta = db.execute(
        select(Venta)
        .options(
            selectinload(Venta.detalles).selectinload(DetalleVenta.producto),
            selectinload(Venta.detalles).selectinload(DetalleVenta.presentacion),
            selectinload(Venta.usuario),
        )
        .where(Venta.id == venta_id)
    ).scalar_one()
    return venta


@router.get("", response_model=Pagina[VentaOut])
def listar(
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
    usuario_id: int | None = None,
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.VENTAS_VER)),
    db: Session = Depends(get_db),
) -> Pagina[VentaOut]:
    filtros = []
    if desde is not None:
        filtros.append(Venta.fecha >= desde)
    if hasta is not None:
        filtros.append(Venta.fecha <= hasta)
    if estado:
        filtros.append(Venta.estado == estado)
    if usuario_id is not None:
        filtros.append(Venta.usuario_id == usuario_id)

    total = db.execute(
        select(func.count()).select_from(Venta).where(*filtros)
    ).scalar_one()
    filas = db.execute(
        select(Venta)
        .options(
            selectinload(Venta.detalles).selectinload(DetalleVenta.producto),
            selectinload(Venta.detalles).selectinload(DetalleVenta.presentacion),
            selectinload(Venta.usuario),
        )
        .where(*filtros)
        .order_by(Venta.fecha.desc(), Venta.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).scalars().all()
    return Pagina[VentaOut](
        items=[VentaOut(**servicio.venta_a_dict(v)) for v in filas],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )


@router.get("/{venta_id}", response_model=VentaOut)
def obtener(
    venta_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.VENTAS_VER)),
    db: Session = Depends(get_db),
) -> VentaOut:
    return VentaOut(**servicio.venta_a_dict(_cargar(db, venta_id)))


@router.post("/{venta_id}/anular", response_model=VentaOut)
def anular(
    venta_id: int,
    datos: AnulacionVentaIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.VENTAS_ANULAR)),
    db: Session = Depends(get_db),
) -> VentaOut:
    venta = servicio.anular(db, venta_id, datos.motivo, usuario.id)
    auditoria.registrar(
        db,
        accion="venta.anular",
        entidad="venta",
        entidad_id=venta.id,
        actor_id=usuario.id,
        detalle={"numero": venta.numero, "motivo": datos.motivo},
    )
    db.commit()
    db.refresh(venta)
    return VentaOut(**servicio.venta_a_dict(_cargar(db, venta.id)))

