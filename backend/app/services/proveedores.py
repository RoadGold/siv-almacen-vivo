"""Servicios de proveedores y su relación con productos."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    DetalleAbastecimiento,
    Abastecimiento,
    PresentacionProducto,
    Producto,
    ProductoProveedor,
    Proveedor,
)
from app.domain.unidades import ErrorNegocio, dec, num


def listar_proveedores(
    db: Session,
    *,
    q: str | None = None,
    activo: bool | None = True,
    pagina: int = 1,
    tamano: int = 20,
) -> tuple[list[Proveedor], int]:
    pagina = max(1, pagina)
    tamano = max(1, min(tamano, 200))

    filtros = []
    if activo is not None:
        filtros.append(Proveedor.activo.is_(activo))

    consulta = select(Proveedor)
    if q:
        texto = q.strip().lower()
        condiciones = [
            func.lower(Proveedor.razon_social).like(f"%{texto}%"),
            func.lower(Proveedor.nombre_comercial).like(f"%{texto}%"),
            func.lower(Proveedor.codigo).like(f"%{texto}%"),
            func.lower(Proveedor.ruc).like(f"%{texto}%"),
            func.lower(Proveedor.contacto).like(f"%{texto}%"),
        ]
        consulta = consulta.where(or_(*condiciones))

    total = db.execute(
        select(func.count()).select_from(Proveedor).where(*filtros)
    ).scalar_one()
    if q:
        total = db.execute(
            select(func.count())
            .select_from(Proveedor)
            .where(*filtros)
            .where(
                or_(
                    func.lower(Proveedor.razon_social).like(f"%{q.strip().lower()}%"),
                    func.lower(Proveedor.nombre_comercial).like(f"%{q.strip().lower()}%"),
                    func.lower(Proveedor.codigo).like(f"%{q.strip().lower()}%"),
                    func.lower(Proveedor.ruc).like(f"%{q.strip().lower()}%"),
                    func.lower(Proveedor.contacto).like(f"%{q.strip().lower()}%"),
                )
            )
        ).scalar_one()

    proveedores = db.execute(
        consulta.where(*filtros)
        .order_by(Proveedor.razon_social)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).scalars().all()
    return list(proveedores), total


def obtener_proveedor(db: Session, proveedor_id: int) -> Proveedor:
    proveedor = db.get(Proveedor, proveedor_id)
    if proveedor is None:
        raise ErrorNegocio("El proveedor no existe.", detalle={"proveedor_id": proveedor_id})
    return proveedor


def crear_proveedor(db: Session, datos: dict[str, Any]) -> Proveedor:
    codigo = datos["codigo"].strip()
    existe = db.execute(
        select(Proveedor).where(func.lower(Proveedor.codigo) == codigo.lower())
    ).scalar_one_or_none()
    if existe is not None:
        raise ErrorNegocio("Ya existe un proveedor con ese código.", detalle={"campo": "codigo"})
    ruc = (datos.get("ruc") or "").strip() or None
    if ruc:
        ruc_existente = db.execute(
            select(Proveedor).where(Proveedor.ruc == ruc)
        ).scalar_one_or_none()
        if ruc_existente is not None:
            raise ErrorNegocio("Ya existe un proveedor con ese RUC.", detalle={"campo": "ruc"})
    proveedor = Proveedor(
        codigo=codigo,
        razon_social=datos["razon_social"].strip(),
        nombre_comercial=(datos.get("nombre_comercial") or "").strip() or None,
        ruc=ruc,
        telefono=(datos.get("telefono") or "").strip() or None,
        contacto=(datos.get("contacto") or "").strip() or None,
        direccion=(datos.get("direccion") or "").strip() or None,
        email=(datos.get("email") or "").strip() or None,
        observaciones=datos.get("observaciones"),
        activo=bool(datos.get("activo", True)),
    )
    db.add(proveedor)
    db.flush()
    return proveedor


def actualizar_proveedor(db: Session, proveedor_id: int, cambios: dict[str, Any]) -> Proveedor:
    proveedor = obtener_proveedor(db, proveedor_id)
    for campo in (
        "razon_social",
        "nombre_comercial",
        "ruc",
        "telefono",
        "contacto",
        "direccion",
        "email",
        "observaciones",
    ):
        if campo in cambios and cambios[campo] is not None:
            valor = cambios[campo]
            setattr(proveedor, campo, str(valor).strip() or None)
    if "activo" in cambios and cambios["activo"] is not None:
        proveedor.activo = bool(cambios["activo"])
    db.flush()
    return proveedor


def vincular_producto(
    db: Session,
    *,
    producto_id: int,
    proveedor_id: int,
    habitual: bool = False,
    presentacion_id: int | None = None,
    observacion: str | None = None,
) -> ProductoProveedor:
    if db.get(Producto, producto_id) is None:
        raise ErrorNegocio("El producto no existe.")
    obtener_proveedor(db, proveedor_id)
    vinculo = db.execute(
        select(ProductoProveedor).where(
            ProductoProveedor.producto_id == producto_id,
            ProductoProveedor.proveedor_id == proveedor_id,
        )
    ).scalar_one_or_none()
    if vinculo is None:
        vinculo = ProductoProveedor(
            producto_id=producto_id,
            proveedor_id=proveedor_id,
            habitual=habitual,
            presentacion_id=presentacion_id,
            observacion=observacion,
        )
        db.add(vinculo)
    else:
        vinculo.habitual = habitual
        if presentacion_id is not None:
            vinculo.presentacion_id = presentacion_id
        if observacion is not None:
            vinculo.observacion = observacion
    db.flush()
    return vinculo


def productos_del_proveedor(db: Session, proveedor_id: int) -> list[dict[str, Any]]:
    """Productos habituales del proveedor, con presentación y último costo."""
    filas = db.execute(
        select(ProductoProveedor, Producto, PresentacionProducto)
        .join(Producto, Producto.id == ProductoProveedor.producto_id)
        .outerjoin(
            PresentacionProducto,
            PresentacionProducto.id == ProductoProveedor.presentacion_id,
        )
        .where(ProductoProveedor.proveedor_id == proveedor_id)
        .order_by(Producto.nombre)
    ).all()

    resultado = []
    for vinculo, producto, presentacion in filas:
        resultado.append(
            {
                "id": vinculo.id,
                "producto_id": producto.id,
                "proveedor_id": proveedor_id,
                "codigo": producto.codigo,
                "nombre": producto.nombre,
                "unidad_base": producto.unidad_base.nombre if producto.unidad_base else None,
                "activo": producto.activo,
                "presentacion_id": vinculo.presentacion_id,
                "presentacion_nombre": presentacion.nombre if presentacion else None,
                "factor_base": num(presentacion.factor_base) if presentacion else None,
                "ultimo_costo": num(vinculo.ultimo_costo) if vinculo.ultimo_costo else None,
                "ultima_fecha_compra": vinculo.ultima_fecha_compra,
                "habitual": vinculo.habitual,
                "observacion": vinculo.observacion,
            }
        )
    return resultado


def historial_abastecimientos(
    db: Session, proveedor_id: int, limite: int = 50
) -> list[dict[str, Any]]:
    filas = db.execute(
        select(Abastecimiento)
        .where(Abastecimiento.proveedor_id == proveedor_id)
        .order_by(Abastecimiento.fecha.desc(), Abastecimiento.id.desc())
        .limit(limite)
    ).scalars().all()
    return [
        {
            "id": a.id,
            "numero": a.numero,
            "fecha": a.fecha,
            "documento": a.documento,
            "estado": a.estado.value,
            "total": num(a.total),
        }
        for a in filas
    ]


def costos_historicos(
    db: Session, *, producto_id: int | None = None, proveedor_id: int | None = None, limite: int = 200
) -> list[dict[str, Any]]:
    consulta = (
        select(
            DetalleAbastecimiento,
            Abastecimiento,
            Producto,
            Proveedor,
        )
        .join(Abastecimiento, Abastecimiento.id == DetalleAbastecimiento.abastecimiento_id)
        .join(Producto, Producto.id == DetalleAbastecimiento.producto_id)
        .join(Proveedor, Proveedor.id == Abastecimiento.proveedor_id)
        .where(Abastecimiento.estado == "CONFIRMADO")
    )
    if producto_id is not None:
        consulta = consulta.where(DetalleAbastecimiento.producto_id == producto_id)
    if proveedor_id is not None:
        consulta = consulta.where(Abastecimiento.proveedor_id == proveedor_id)

    filas = db.execute(consulta.order_by(Abastecimiento.fecha.desc()).limit(limite)).all()
    resultado = []
    for detalle, abastecimiento, producto, proveedor in filas:
        presentacion = db.get(PresentacionProducto, detalle.presentacion_id)
        resultado.append(
            {
                "producto_id": producto.id,
                "producto": producto.nombre,
                "proveedor_id": proveedor.id,
                "proveedor": proveedor.razon_social,
                "presentacion": presentacion.nombre if presentacion else "",
                "costo_unitario": num(detalle.costo_unitario),
                "fecha": abastecimiento.fecha.isoformat(),
                "documento": abastecimiento.documento,
                "cantidad": num(detalle.cantidad),
            }
        )
    return resultado


def actualizar_costo_referencia(db: Session, producto_id: int, proveedor_id: int) -> None:
    """Guarda el último costo y la última fecha de compra del vínculo."""
    vinculo = db.execute(
        select(ProductoProveedor).where(
            ProductoProveedor.producto_id == producto_id,
            ProductoProveedor.proveedor_id == proveedor_id,
        )
    ).scalar_one_or_none()
    if vinculo is None:
        return
    ultimo = db.execute(
        select(DetalleAbastecimiento, Abastecimiento)
        .join(Abastecimiento, Abastecimiento.id == DetalleAbastecimiento.abastecimiento_id)
        .where(
            DetalleAbastecimiento.producto_id == producto_id,
            Abastecimiento.proveedor_id == proveedor_id,
            Abastecimiento.estado == "CONFIRMADO",
        )
        .order_by(Abastecimiento.fecha.desc(), DetalleAbastecimiento.id.desc())
        .limit(1)
    ).first()
    if ultimo is None:
        return
    detalle, abastecimiento = ultimo
    vinculo.ultimo_costo = detalle.costo_unitario
    vinculo.ultima_fecha_compra = abastecimiento.fecha or date.today()
    db.flush()


__all__ = [
    "actualizar_costo_referencia",
    "actualizar_proveedor",
    "costos_historicos",
    "crear_proveedor",
    "historial_abastecimientos",
    "listar_proveedores",
    "obtener_proveedor",
    "productos_del_proveedor",
    "vincular_producto",
]

