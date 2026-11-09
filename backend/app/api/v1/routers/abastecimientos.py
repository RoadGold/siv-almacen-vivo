"""Endpoints de abastecimientos (recepción de mercadería)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Abastecimiento, Usuario
from app.db.session import get_db
from app.schemas.abastecimientos import (
    AbastecimientoIn,
    AbastecimientoOut,
    AnulacionIn,
    PrevisualizacionOut,
)
from app.schemas.common import Pagina
from app.services import abastecimientos as servicio
from app.services import auditoria

router = APIRouter(prefix="/abastecimientos", tags=["Abastecimientos"])


@router.post("/previsualizar", response_model=PrevisualizacionOut)
def previsualizar(
    datos: AbastecimientoIn,
    _: Usuario = Depends(requiere_permiso(Permiso.ABASTECIMIENTOS_CREAR)),
    db: Session = Depends(get_db),
) -> PrevisualizacionOut:
    return PrevisualizacionOut(**servicio.previsualizar(db, datos.model_dump()))


@router.post("", response_model=AbastecimientoOut, status_code=status.HTTP_201_CREATED)
def confirmar(
    datos: AbastecimientoIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.ABASTECIMIENTOS_CREAR)),
    db: Session = Depends(get_db),
) -> AbastecimientoOut:
    abastecimiento = servicio.confirmar(db, datos.model_dump(), usuario.id)
    auditoria.registrar(
        db,
        accion="abastecimiento.confirmar",
        entidad="abastecimiento",
        entidad_id=abastecimiento.id,
        actor_id=usuario.id,
        detalle={"numero": abastecimiento.numero, "total": str(abastecimiento.total)},
    )
    db.commit()
    db.refresh(abastecimiento)
    abastecimiento = db.execute(
        select(Abastecimiento)
        .options(
            selectinload(Abastecimiento.detalles),
            selectinload(Abastecimiento.proveedor),
            selectinload(Abastecimiento.usuario),
        )
        .where(Abastecimiento.id == abastecimiento.id)
    ).scalar_one()
    return AbastecimientoOut(**servicio.abastecimiento_a_dict(abastecimiento))


@router.get("", response_model=Pagina[AbastecimientoOut])
def listar(
    proveedor_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.ABASTECIMIENTOS_VER)),
    db: Session = Depends(get_db),
) -> Pagina[AbastecimientoOut]:
    consulta = select(Abastecimiento).options(
        selectinload(Abastecimiento.detalles),
        selectinload(Abastecimiento.proveedor),
        selectinload(Abastecimiento.usuario),
    )
    if proveedor_id is not None:
        consulta = consulta.where(Abastecimiento.proveedor_id == proveedor_id)
    if desde is not None:
        consulta = consulta.where(Abastecimiento.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(Abastecimiento.fecha <= hasta)
    if estado:
        consulta = consulta.where(Abastecimiento.estado == estado)

    from sqlalchemy import func

    total = db.execute(
        select(func.count()).select_from(consulta.subquery())
    ).scalar_one()
    filas = db.execute(
        consulta.order_by(Abastecimiento.fecha.desc(), Abastecimiento.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).scalars().all()
    return Pagina[AbastecimientoOut](
        items=[AbastecimientoOut(**servicio.abastecimiento_a_dict(a)) for a in filas],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )


@router.get("/{abastecimiento_id}", response_model=AbastecimientoOut)
def obtener(
    abastecimiento_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.ABASTECIMIENTOS_VER)),
    db: Session = Depends(get_db),
) -> AbastecimientoOut:
    abastecimiento = db.execute(
        select(Abastecimiento)
        .options(
            selectinload(Abastecimiento.detalles),
            selectinload(Abastecimiento.proveedor),
            selectinload(Abastecimiento.usuario),
        )
        .where(Abastecimiento.id == abastecimiento_id)
    ).scalar_one_or_none()
    if abastecimiento is None:
        from app.domain.unidades import ErrorNegocio

        raise ErrorNegocio("El abastecimiento no existe.")
    return AbastecimientoOut(**servicio.abastecimiento_a_dict(abastecimiento))


@router.post("/{abastecimiento_id}/anular", response_model=AbastecimientoOut)
def anular(
    abastecimiento_id: int,
    datos: AnulacionIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.ABASTECIMIENTOS_ANULAR)),
    db: Session = Depends(get_db),
) -> AbastecimientoOut:
    abastecimiento = servicio.anular(db, abastecimiento_id, datos.motivo, usuario.id)
    auditoria.registrar(
        db,
        accion="abastecimiento.anular",
        entidad="abastecimiento",
        entidad_id=abastecimiento.id,
        actor_id=usuario.id,
        detalle={"numero": abastecimiento.numero, "motivo": datos.motivo},
    )
    db.commit()
    db.refresh(abastecimiento)
    abastecimiento = db.execute(
        select(Abastecimiento)
        .options(
            selectinload(Abastecimiento.detalles),
            selectinload(Abastecimiento.proveedor),
            selectinload(Abastecimiento.usuario),
        )
        .where(Abastecimiento.id == abastecimiento.id)
    ).scalar_one()
    return AbastecimientoOut(**servicio.abastecimiento_a_dict(abastecimiento))
