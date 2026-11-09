"""Endpoints de inventario: existencias, kardex, radar, ajustes y conciliación."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.domain.unidades import num
from app.schemas.catalogo import ProductoFicha
from app.schemas.common import Pagina
from app.schemas.inventario import (
    AjusteIn,
    AjusteOut,
    ConciliacionOut,
    ExistenciaOut,
    MovimientoOut,
    RadarReposicionItem,
)
from app.schemas.importacion import InventarioInicialIn
from app.domain.unidades import ErrorNegocio, num
from app.services import existencias as servicio
from app.services import inventario as motor

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/existencias", response_model=Pagina[ExistenciaOut])
def listar_existencias(
    almacen_id: int | None = None,
    q: str | None = Query(default=None, max_length=120),
    categoria_id: int | None = None,
    estado: str | None = Query(default=None, pattern="^(agotado|bajo_minimo|disponible)$"),
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=25, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_VER)),
    db: Session = Depends(get_db),
) -> Pagina[ExistenciaOut]:
    items, total = servicio.listar_existencias(
        db,
        almacen_id=almacen_id,
        q=q,
        categoria_id=categoria_id,
        estado=estado,
        pagina=pagina,
        tamano=tamano,
    )
    return Pagina[ExistenciaOut](
        items=[ExistenciaOut(**i) for i in items],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )


@router.get("/productos/{producto_id}/ficha", response_model=ProductoFicha)
def ficha_producto(
    producto_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_VER)),
    db: Session = Depends(get_db),
) -> ProductoFicha:
    """Ficha viva: existencias, proveedores y huella del producto."""
    return ProductoFicha(**servicio.ficha_producto(db, producto_id))


@router.get("/movimientos", response_model=Pagina[MovimientoOut])
def movimientos(
    producto_id: int | None = None,
    almacen_id: int | None = None,
    tipo: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=50, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_VER)),
    db: Session = Depends(get_db),
) -> Pagina[MovimientoOut]:
    items, total = servicio.movimientos(
        db,
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
        pagina=pagina,
        tamano=tamano,
    )
    return Pagina[MovimientoOut](
        items=[MovimientoOut(**i) for i in items],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )


@router.get("/radar-reposicion", response_model=list[RadarReposicionItem])
def radar(
    almacen_id: int | None = None,
    limite: int = Query(default=50, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_VER)),
    db: Session = Depends(get_db),
) -> list[RadarReposicionItem]:
    return [RadarReposicionItem(**i) for i in servicio.radar_reposicion(db, almacen_id=almacen_id, limite=limite)]


@router.post("/ajustes", response_model=AjusteOut, status_code=status.HTTP_201_CREATED)
def crear_ajuste(
    datos: AjusteIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_AJUSTAR)),
    db: Session = Depends(get_db),
) -> AjusteOut:
    ajuste = servicio.crear_ajuste(
        db,
        almacen_id=datos.almacen_id,
        producto_id=datos.producto_id,
        cantidad_base=datos.cantidad_base,
        motivo=datos.motivo,
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(ajuste)
    return AjusteOut(
        id=ajuste.id,
        numero=ajuste.numero,
        almacen_id=ajuste.almacen_id,
        producto_id=ajuste.producto_id,
        tipo=ajuste.tipo.value,
        cantidad_base=num(ajuste.cantidad_base),
        motivo=ajuste.motivo,
        estado=ajuste.estado.value,
        created_at=ajuste.created_at,
    )


@router.post("/inventario-inicial")
def inventario_inicial(
    datos: InventarioInicialIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_AJUSTAR)),
    db: Session = Depends(get_db),
) -> dict:
    """Carga inicial de existencias (operación administrativa, no es una compra)."""
    almacen_id = datos.almacen_id
    if almacen_id is None:
        from app.db.models import Almacen

        almacen = db.execute(
            select(Almacen).where(Almacen.activo.is_(True)).order_by(Almacen.id)
        ).scalars().first()
        if almacen is None:
            raise ErrorNegocio("No hay un almacén activo configurado.")
        almacen_id = almacen.id
    resultado = servicio.registrar_saldo_inicial(
        db,
        almacen_id=almacen_id,
        lineas=[l.model_dump() for l in datos.lineas],
        usuario_id=usuario.id,
        referencia=datos.referencia,
    )
    db.commit()
    return resultado


@router.get("/conciliacion", response_model=ConciliacionOut)
def conciliacion(
    almacen_id: int | None = None,
    _: Usuario = Depends(requiere_permiso(Permiso.INVENTARIO_AJUSTAR)),
    db: Session = Depends(get_db),
) -> ConciliacionOut:
    """Compara saldos del kardex con la tabla de existencias, sin alterar datos."""
    from app.db.models import Existencia, MovimientoInventario

    diferencias = motor.conciliar(db, almacen_id)
    negativos = motor.existencias_negativas(db)
    detalle_mov = db.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
    detalle_exi = db.execute(select(func.count()).select_from(Existencia)).scalar_one()
    return ConciliacionOut(
        fecha=date.today().isoformat(),
        diferencias=diferencias,
        existencias_negativas=negativos,
        detalle_movimientos=detalle_mov,
        detalle_existencias=detalle_exi,
    )
