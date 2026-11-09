"""Endpoints de catálogo: productos, presentaciones, unidades, categorías y marcas."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, requiere_permiso
from app.core.permissions import Permiso
from app.db.models import Usuario
from app.db.session import get_db
from app.domain.unidades import ErrorNegocio
from app.schemas.catalogo import (
    CategoriaCreate,
    CategoriaOut,
    MarcaCreate,
    MarcaOut,
    PresentacionIn,
    PresentacionOut,
    PresentacionUpdate,
    ProductoIn,
    ProductoOut,
    ProductoUpdate,
    UnidadMedidaCreate,
    UnidadMedidaOut,
)
from app.schemas.common import Pagina
from app.schemas.importacion import (
    FilaImportadaOut,
    PrevisualizacionImportacion,
    ResultadoImportacion,
    ResumenImportacion as ResultadoResumen,
)
from app.services import catalogo, importador

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])


@router.get("/productos", response_model=Pagina[ProductoOut])
def listar_productos(
    q: str | None = Query(default=None, max_length=120),
    categoria_id: int | None = None,
    marca_id: int | None = None,
    activo: bool | None = True,
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=200),
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> Pagina[ProductoOut]:
    items, total = catalogo.listar_productos(
        db,
        q=q,
        categoria_id=categoria_id,
        marca_id=marca_id,
        activo=activo,
        pagina=pagina,
        tamano=tamano,
    )
    return Pagina[ProductoOut](
        items=[ProductoOut(**i) for i in items],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=(total + tamano - 1) // tamano if tamano else 0,
    )


@router.get("/productos/{producto_id}", response_model=ProductoOut)
def obtener_producto(
    producto_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> ProductoOut:
    producto = catalogo.obtener_producto(db, producto_id)
    return ProductoOut(**catalogo.producto_a_dict(producto))


@router.post(
    "/productos",
    response_model=ProductoOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_producto(
    datos: ProductoIn,
    usuario: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> ProductoOut:
    producto = catalogo.crear_producto(db, datos.model_dump())
    db.commit()
    producto = catalogo.obtener_producto(db, producto.id)
    return ProductoOut(**catalogo.producto_a_dict(producto))


@router.patch("/productos/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: int,
    cambios: ProductoUpdate,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> ProductoOut:
    producto = catalogo.actualizar_producto(db, producto_id, cambios.model_dump(exclude_unset=True))
    db.commit()
    producto = catalogo.obtener_producto(db, producto.id)
    return ProductoOut(**catalogo.producto_a_dict(producto))


@router.post(
    "/productos/{producto_id}/presentaciones",
    response_model=PresentacionOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_presentacion(
    producto_id: int,
    datos: PresentacionIn,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> PresentacionOut:
    presentacion = catalogo.crear_presentacion(db, producto_id, datos.model_dump())
    db.commit()
    return PresentacionOut(**catalogo.presentacion_a_dict(presentacion))


@router.patch("/presentaciones/{presentacion_id}", response_model=PresentacionOut)
def actualizar_presentacion(
    presentacion_id: int,
    cambios: PresentacionUpdate,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> PresentacionOut:
    presentacion = catalogo.actualizar_presentacion(
        db, presentacion_id, cambios.model_dump(exclude_unset=True)
    )
    db.commit()
    return PresentacionOut(**catalogo.presentacion_a_dict(presentacion))


@router.delete("/presentaciones/{presentacion_id}", response_model=PresentacionOut)
def desactivar_presentacion(
    presentacion_id: int,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> PresentacionOut:
    presentacion = catalogo.desactivar_presentacion(db, presentacion_id)
    db.commit()
    return PresentacionOut(**catalogo.presentacion_a_dict(presentacion))


@router.get("/unidades", response_model=list[UnidadMedidaOut])
def listar_unidades(
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> list[UnidadMedidaOut]:
    return [UnidadMedidaOut.model_validate(u) for u in catalogo.listar_unidades(db)]


@router.post(
    "/unidades", response_model=UnidadMedidaOut, status_code=status.HTTP_201_CREATED
)
def crear_unidad(
    datos: UnidadMedidaCreate,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> UnidadMedidaOut:
    unidad = catalogo.crear_unidad(db, datos.model_dump())
    db.commit()
    return UnidadMedidaOut.model_validate(unidad)


@router.get("/categorias", response_model=list[CategoriaOut])
def listar_categorias(
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> list[CategoriaOut]:
    return [CategoriaOut.model_validate(c) for c in catalogo.listar_categorias(db)]


@router.post(
    "/categorias", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED
)
def crear_categoria(
    datos: CategoriaCreate,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> CategoriaOut:
    categoria = catalogo.crear_categoria(db, datos.nombre)
    db.commit()
    return CategoriaOut.model_validate(categoria)


@router.get("/marcas", response_model=list[MarcaOut])
def listar_marcas(
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> list[MarcaOut]:
    return [MarcaOut.model_validate(m) for m in catalogo.listar_marcas(db)]


@router.post("/marcas", response_model=MarcaOut, status_code=status.HTTP_201_CREATED)
def crear_marca(
    datos: MarcaCreate,
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> MarcaOut:
    marca = catalogo.crear_marca(db, datos.nombre)
    db.commit()
    return MarcaOut.model_validate(marca)


@router.get("/importar/plantilla")
def plantilla_importacion(
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
) -> Response:
    """Plantilla Excel para la importación del catálogo."""
    contenido = importador.plantilla_excel()
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="plantilla-catalogo-siv.xlsx"'
        },
    )


@router.post("/importar/previsualizar", response_model=PrevisualizacionImportacion)
async def previsualizar_importacion(
    archivo: UploadFile = File(...),
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> PrevisualizacionImportacion:
    """Analiza el archivo sin escribir nada en la base de datos."""
    contenido = await archivo.read()
    resultado = importador.previsualizar(db, contenido, archivo.filename or "")
    return PrevisualizacionImportacion(
        resumen=ResultadoResumen(**resultado["resumen"]),
        filas=[FilaImportadaOut(**f) for f in resultado["filas"]],
    )


@router.post("/importar/confirmar", response_model=ResultadoImportacion)
async def confirmar_importacion(
    archivo: UploadFile = File(...),
    aplicar_stock_inicial: bool = Query(default=True),
    almacen_id: int | None = None,
    usuario: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_GESTIONAR)),
    db: Session = Depends(get_db),
) -> ResultadoImportacion:
    """Aplica las filas válidas del archivo."""
    contenido = await archivo.read()
    resultado = importador.confirmar(
        db,
        contenido,
        archivo.filename or "",
        aplicar_stock_inicial=aplicar_stock_inicial,
        almacen_id=almacen_id,
        usuario_id=usuario.id,
    )
    db.commit()
    return ResultadoImportacion(
        importadas=resultado["importadas"],
        productos_creados=resultado["productos_creados"],
        productos_actualizados=resultado["productos_actualizados"],
        rechazadas=resultado["rechazadas"],
        aplicadas=[FilaImportadaOut(**f) for f in resultado["aplicadas"]],
        errores=[FilaImportadaOut(**f) for f in resultado["errores"]],
    )


@router.get("/buscar", response_model=list[dict[str, Any]])
def busqueda_universal(
    q: str = Query(min_length=1, max_length=120),
    limite: int = Query(default=8, ge=1, le=30),
    _: Usuario = Depends(requiere_permiso(Permiso.CATALOGO_VER)),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Buscador universal: agrupa resultados por tipo (plan §3)."""
    from app.services.proveedores import listar_proveedores

    productos, _ = catalogo.listar_productos(db, q=q, pagina=1, tamano=limite)
    proveedores, _ = listar_proveedores(db, q=q, pagina=1, tamano=limite)
    return [
        {
            "tipo": "producto",
            "id": p["id"],
            "titulo": p["nombre"],
            "detalle": p["codigo"],
        }
        for p in productos
    ] + [
        {
            "tipo": "proveedor",
            "id": pr.id,
            "titulo": pr.razon_social,
            "detalle": pr.codigo,
        }
        for pr in proveedores
    ]
