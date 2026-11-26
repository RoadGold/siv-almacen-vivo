"""Endpoints de administración: usuarios, roles y auditoría."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, permisos_usuario, requiere_permiso
from app.core.permissions import Permiso
from app.core.security import hash_password
from app.db.models import Auditoria, Rol, Usuario, UsuarioRol
from app.db.session import get_db
from app.domain.unidades import ErrorNegocio
from app.schemas.auth import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.schemas.common import Pagina
from app.services import auditoria as servicio_auditoria

router = APIRouter(prefix="/admin", tags=["Administración"])


@router.get("/estado-base")
def estado_base(
    _: Usuario = Depends(requiere_permiso(Permiso.ADMIN_AUDITORIA)),
    db: Session = Depends(get_db),
) -> dict:
    """Estado de la base de datos: qué contiene y si está limpia.

    Sirve para comprobar, desde el sistema, que la base no tiene operación
    pendiente y que las existencias cuadran con la suma de los lotes.
    """
    from app.services import inventario as motor

    tablas = [
        "productos",
        "presentaciones_producto",
        "proveedores",
        "marcas",
        "categorias",
        "lotes_inventario",
        "existencias",
        "movimientos_inventario",
        "ventas",
        "detalle_ventas",
        "abastecimientos",
        "detalle_abastecimientos",
        "ajustes_inventario",
        "impresiones_venta",
        "auditoria",
        "usuarios",
        "almacenes",
        "unidades_medida",
        "configuracion",
    ]
    conteos = {
        tabla: db.execute(
            text(f'SELECT COUNT(*) FROM "{tabla}"')
        ).scalar_one()
        for tabla in tablas
    }

    try:
        version_esquema = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    except Exception:  # pragma: no cover - la tabla siempre existe tras migrar
        version_esquema = None

    conciliacion = motor.conciliar(db)
    return {
        "conteos": conteos,
        "version_esquema": version_esquema,
        "diferencias_conciliacion": len(conciliacion),
        "detalle_conciliacion": conciliacion[:20],
        "operacion_pendiente": bool(
            conteos["ventas"]
            or conteos["abastecimientos"]
            or conteos["ajustes_inventario"]
            or conteos["impresiones_venta"]
            or conteos["auditoria"]
        ),
        "tiene_stock": bool(conteos["existencias"]),
    }


@router.get("/usuarios", response_model=Pagina[UsuarioOut])
def listar_usuarios(
    activo: bool | None = None,
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.ADMIN_USUARIOS)),
    db: Session = Depends(get_db),
) -> Pagina[UsuarioOut]:
    filtros = []
    if activo is not None:
        filtros.append(Usuario.activo.is_(activo))
    total = db.execute(
        select(func.count()).select_from(Usuario).where(*filtros)
    ).scalar_one()
    filas = db.execute(
        select(Usuario)
        .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
        .where(*filtros)
        .order_by(Usuario.nombre)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).scalars().all()
    return Pagina[UsuarioOut](
        items=[_usuario_out(u) for u in filas],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )


def _usuario_out(usuario: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        usuario=usuario.usuario,
        activo=usuario.activo,
        roles=[ur.rol.nombre for ur in usuario.roles],
        permisos=sorted(permisos_usuario(usuario)),
        ultimo_acceso=usuario.ultimo_acceso,
    )


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCreate,
    _: Usuario = Depends(requiere_permiso(Permiso.ADMIN_USUARIOS)),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    nombre_usuario = datos.usuario.strip().lower()
    existe = db.execute(
        select(Usuario).where(func.lower(Usuario.usuario) == nombre_usuario)
    ).scalar_one_or_none()
    if existe is not None:
        raise ErrorNegocio("Ya existe un usuario con ese nombre de acceso.")

    rol = db.execute(select(Rol).where(Rol.nombre == datos.rol)).scalar_one_or_none()
    if rol is None:
        raise ErrorNegocio(f"El rol «{datos.rol}» no existe.")

    usuario = Usuario(
        nombre=datos.nombre.strip(),
        usuario=nombre_usuario,
        password_hash=hash_password(datos.password),
        activo=datos.activo,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))
    servicio_auditoria.registrar(
        db,
        accion="usuario.crear",
        entidad="usuario",
        entidad_id=usuario.id,
        actor_id=None,
        detalle={"usuario": nombre_usuario, "rol": datos.rol},
    )
    db.commit()
    db.refresh(usuario)
    return _usuario_out(usuario)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    cambios: UsuarioUpdate,
    usuario_actual: Usuario = Depends(requiere_permiso(Permiso.ADMIN_USUARIOS)),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ErrorNegocio("El usuario no existe.")
    if "nombre" in cambios and cambios.nombre:
        usuario.nombre = cambios.nombre.strip()
    if "activo" in cambios and cambios.activo is not None:
        usuario.activo = bool(cambios.activo)
    if cambios.password:
        usuario.password_hash = hash_password(cambios.password)
    if cambios.rol:
        rol = db.execute(select(Rol).where(Rol.nombre == cambios.rol)).scalar_one_or_none()
        if rol is None:
            raise ErrorNegocio(f"El rol «{cambios.rol}» no existe.")
        usuario.roles.clear()
        db.flush()
        db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))
    servicio_auditoria.registrar(
        db,
        accion="usuario.actualizar",
        entidad="usuario",
        entidad_id=usuario.id,
        actor_id=usuario_actual.id,
        detalle={"campos": list(cambios.model_dump(exclude_unset=True).keys())},
    )
    db.commit()
    db.refresh(usuario)
    return _usuario_out(usuario)


@router.get("/auditoria", response_model=Pagina[dict])
def listar_auditoria(
    entidad: str | None = None,
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=50, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.ADMIN_AUDITORIA)),
    db: Session = Depends(get_db),
) -> Pagina[dict]:
    filtros = []
    if entidad:
        filtros.append(Auditoria.entidad == entidad)
    total = db.execute(
        select(func.count()).select_from(Auditoria).where(*filtros)
    ).scalar_one()
    filas = db.execute(
        select(Auditoria)
        .where(*filtros)
        .order_by(Auditoria.created_at.desc(), Auditoria.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).scalars().all()
    return Pagina[dict](
        items=[
            {
                "id": a.id,
                "actor_id": a.actor_id,
                "accion": a.accion,
                "entidad": a.entidad,
                "entidad_id": a.entidad_id,
                "detalle": a.detalle,
                "created_at": a.created_at,
            }
            for a in filas
        ],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )
