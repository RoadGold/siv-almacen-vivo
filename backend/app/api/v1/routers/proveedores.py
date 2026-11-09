"""Endpoints de proveedores."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.schemas.common import Pagina
from app.schemas.proveedores import (
    CostoHistoricoProveedor,
    ProductoProveedorIn,
    ProductoProveedorOut,
    ProveedorIn,
    ProveedorOut,
    ProveedorUpdate,
)
from app.services import proveedores as servicio

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.get("", response_model=Pagina[ProveedorOut])
def listar_proveedores(
    q: str | None = Query(default=None, max_length=120),
    activo: bool | None = True,
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_VER)),
    db: Session = Depends(get_db),
) -> Pagina[ProveedorOut]:
    items, total = servicio.listar_proveedores(
        db, q=q, activo=activo, pagina=pagina, tamano=tamano
    )
    return Pagina[ProveedorOut](
        items=[ProveedorOut.model_validate(p) for p in items],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )


@router.get("/{proveedor_id}", response_model=ProveedorOut)
def obtener_proveedor(
    proveedor_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_VER)),
    db: Session = Depends(get_db),
) -> ProveedorOut:
    return ProveedorOut.model_validate(servicio.obtener_proveedor(db, proveedor_id))


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    datos: ProveedorIn,
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_GESTIONAR)),
    db: Session = Depends(get_db),
) -> ProveedorOut:
    proveedor = servicio.crear_proveedor(db, datos.model_dump())
    db.commit()
    return ProveedorOut.model_validate(proveedor)


@router.patch("/{proveedor_id}", response_model=ProveedorOut)
def actualizar_proveedor(
    proveedor_id: int,
    cambios: ProveedorUpdate,
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_GESTIONAR)),
    db: Session = Depends(get_db),
) -> ProveedorOut:
    proveedor = servicio.actualizar_proveedor(
        db, proveedor_id, cambios.model_dump(exclude_unset=True)
    )
    db.commit()
    return ProveedorOut.model_validate(proveedor)


@router.get("/{proveedor_id}/productos")
def productos_del_proveedor(
    proveedor_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    servicio.obtener_proveedor(db, proveedor_id)
    return servicio.productos_del_proveedor(db, proveedor_id)


@router.get("/{proveedor_id}/historial")
def historial(
    proveedor_id: int,
    limite: int = Query(default=50, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_VER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    return servicio.historial_abastecimientos(db, proveedor_id, limite)


@router.get("/{proveedor_id}/costos", response_model=list[CostoHistoricoProveedor])
def costos(
    proveedor_id: int,
    producto_id: int | None = None,
    limite: int = Query(default=200, ge=1, le=1000),
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_VER)),
    db: Session = Depends(get_db),
) -> list[CostoHistoricoProveedor]:
    datos = servicio.costos_historicos(
        db, producto_id=producto_id, proveedor_id=proveedor_id, limite=limite
    )
    return [CostoHistoricoProveedor(**d) for d in datos]


@router.post("/vinculos", response_model=ProductoProveedorOut, status_code=status.HTTP_201_CREATED)
def vincular_producto(
    datos: ProductoProveedorIn,
    _: Usuario = Depends(requiere_permiso(Permiso.PROVEEDORES_GESTIONAR)),
    db: Session = Depends(get_db),
) -> ProductoProveedorOut:
    vinculo = servicio.vincular_producto(
        db,
        producto_id=datos.producto_id,
        proveedor_id=datos.proveedor_id,
        habitual=datos.habitual,
        presentacion_id=datos.presentacion_id,
        observacion=datos.observacion,
    )
    db.commit()
    return ProductoProveedorOut.model_validate(vinculo)
