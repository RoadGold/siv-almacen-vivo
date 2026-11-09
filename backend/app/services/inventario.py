"""Motor de inventario: existencias, movimientos y conciliaciÃ³n (Fase 3).

Todas las funciones trabajan dentro de la transacciÃ³n abierta por el llamador.
Ninguna hace commit: la atomicidad la garantiza el servicio de operaciÃ³n.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import Existencia, MovimientoInventario, TipoMovimiento
from app.domain.costing import costo_promedio_tras_entrada, costo_promedio_tras_salida
from app.domain.unidades import ZERO, ErrorNegocio, ErrorStockInsuficiente, dec, num, q4, q6


def asegurar_existencia(db: Session, almacen_id: int, producto_id: int) -> int:
    """Crea la fila de existencia si falta y devuelve su id. Portable en PG."""
    stmt = (
        pg_insert(Existencia)
        .values(almacen_id=almacen_id, producto_id=producto_id, cantidad_base=0, costo_promedio_base=0)
        .on_conflict_do_nothing(index_elements=["almacen_id", "producto_id"])
    )
    db.execute(stmt)
    db.flush()
    return db.execute(
        select(Existencia.id).where(
            Existencia.almacen_id == almacen_id, Existencia.producto_id == producto_id
        )
    ).scalar_one()


def bloquear_existencia(db: Session, almacen_id: int, producto_id: int) -> Existencia:
    """Bloquea la fila de existencia (SELECT ... FOR UPDATE) para evitar carreras."""
    asegurar_existencia(db, almacen_id, producto_id)
    existencia = db.execute(
        select(Existencia)
        .where(
            Existencia.almacen_id == almacen_id,
            Existencia.producto_id == producto_id,
        )
        .with_for_update()
    ).scalar_one()
    return existencia


def registrar_movimiento(
    db: Session,
    *,
    producto_id: int,
    almacen_id: int,
    tipo: TipoMovimiento,
    cantidad_base_signed: Decimal,
    saldo_base_despues: Decimal,
    costo_unitario_base: Decimal,
    origen_tipo: str,
    origen_id: int,
    usuario_id: int | None,
    referencia: str | None = None,
) -> MovimientoInventario:
    movimiento = MovimientoInventario(
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo=tipo,
        cantidad_base_signed=q4(cantidad_base_signed),
        saldo_base_despues=q4(saldo_base_despues),
        costo_unitario_base=q6(costo_unitario_base),
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        usuario_id=usuario_id,
        referencia=referencia,
    )
    db.add(movimiento)
    db.flush()
    return movimiento


def aplicar_entrada(
    db: Session,
    *,
    almacen_id: int,
    producto_id: int,
    cantidad_base: Decimal,
    costo_unitario_base: Decimal,
    tipo: TipoMovimiento,
    origen_tipo: str,
    origen_id: int,
    usuario_id: int | None,
    referencia: str | None = None,
) -> Existencia:
    """Suma stock y recalcula el costo promedio ponderado mÃ³vil."""
    if cantidad_base <= 0:
        raise ErrorNegocio("La cantidad de entrada debe ser mayor que cero.")
    existencia = bloquear_existencia(db, almacen_id, producto_id)
    cantidad_previa = dec(existencia.cantidad_base)
    costo_previo = dec(existencia.costo_promedio_base)

    nuevo_costo = costo_promedio_tras_entrada(
        cantidad_previa, costo_previo, cantidad_base, costo_unitario_base
    )
    existencia.cantidad_base = q4(cantidad_previa + cantidad_base)
    existencia.costo_promedio_base = nuevo_costo
    db.flush()

    registrar_movimiento(
        db,
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo=tipo,
        cantidad_base_signed=cantidad_base,
        saldo_base_despues=dec(existencia.cantidad_base),
        costo_unitario_base=costo_unitario_base,
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        usuario_id=usuario_id,
        referencia=referencia,
    )
    return existencia


def aplicar_salida(
    db: Session,
    *,
    almacen_id: int,
    producto_id: int,
    cantidad_base: Decimal,
    tipo: TipoMovimiento,
    origen_tipo: str,
    origen_id: int,
    usuario_id: int | None,
    referencia: str | None = None,
    permitir_negativo: bool = False,
) -> Existencia:
    """Resta stock validando disponibilidad y recalcula el costo promedio."""
    if cantidad_base <= 0:
        raise ErrorNegocio("La cantidad de salida debe ser mayor que cero.")
    existencia = bloquear_existencia(db, almacen_id, producto_id)
    cantidad_previa = dec(existencia.cantidad_base)
    costo_previo = dec(existencia.costo_promedio_base)

    if cantidad_base > cantidad_previa and not permitir_negativo:
        raise ErrorStockInsuficiente(
            "No hay stock suficiente para completar la operaciÃ³n.",
            detalle={
                "producto_id": producto_id,
                "cantidad_solicitada": num(q4(cantidad_base)),
                "saldo_disponible": num(q4(cantidad_previa)),
            },
        )

    costo_salida = costo_previo
    existencia.cantidad_base = q4(cantidad_previa - cantidad_base)
    existencia.costo_promedio_base = costo_promedio_tras_salida(
        cantidad_previa, costo_previo, cantidad_base, costo_salida
    )
    db.flush()

    registrar_movimiento(
        db,
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo=tipo,
        cantidad_base_signed=-cantidad_base,
        saldo_base_despues=dec(existencia.cantidad_base),
        costo_unitario_base=costo_salida,
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        usuario_id=usuario_id,
        referencia=referencia,
    )
    return existencia


def existencia_actual(db: Session, almacen_id: int, producto_id: int) -> Existencia | None:
    return db.execute(
        select(Existencia).where(
            Existencia.almacen_id == almacen_id, Existencia.producto_id == producto_id
        )
    ).scalar_one_or_none()


def saldo_movimientos(db: Session, almacen_id: int, producto_id: int) -> Decimal:
    """Suma de movimientos: la verdad histÃ³rica del kardex."""
    total = db.execute(
        select(func.coalesce(func.sum(MovimientoInventario.cantidad_base_signed), 0)).where(
            MovimientoInventario.almacen_id == almacen_id,
            MovimientoInventario.producto_id == producto_id,
        )
    ).scalar()
    return dec(total or 0)


def conciliar(db: Session, almacen_id: int | None = None) -> list[dict]:
    """Compara la suma del kardex con la tabla de existencias (plan Â§7.4).

    Devuelve las diferencias detectadas sin alterar ningÃºn dato.
    """
    stmt = select(
        Existencia.almacen_id,
        Existencia.producto_id,
        Existencia.cantidad_base,
        func.coalesce(
            func.sum(MovimientoInventario.cantidad_base_signed)
            .filter(MovimientoInventario.almacen_id == Existencia.almacen_id)
            .filter(MovimientoInventario.producto_id == Existencia.producto_id),
            0,
        ),
    ).select_from(Existencia).outerjoin(
        MovimientoInventario,
        (MovimientoInventario.almacen_id == Existencia.almacen_id)
        & (MovimientoInventario.producto_id == Existencia.producto_id),
    )

    if almacen_id is not None:
        stmt = stmt.where(Existencia.almacen_id == almacen_id)

    stmt = stmt.group_by(Existencia.almacen_id, Existencia.producto_id, Existencia.cantidad_base)

    diferencias = []
    for alm_id, prod_id, cantidad_tabla, cantidad_mov in db.execute(stmt):
        if dec(cantidad_tabla) != dec(cantidad_mov):
            diferencias.append(
                {
                    "almacen_id": alm_id,
                    "producto_id": prod_id,
                    "saldo_existencias": num(q4(dec(cantidad_tabla))),
                    "saldo_movimientos": num(q4(dec(cantidad_mov))),
                    "diferencia": num(q4(dec(cantidad_tabla) - dec(cantidad_mov))),
                }
            )
    return diferencias


def existencias_negativas(db: Session) -> list[dict]:
    filas = db.execute(
        select(Existencia.almacen_id, Existencia.producto_id, Existencia.cantidad_base).where(
            Existencia.cantidad_base < 0
        )
    ).all()
    return [
        {"almacen_id": a, "producto_id": p, "cantidad_base": num(q4(dec(c)))}
        for a, p, c in filas
    ]


def stock_total(db: Session, almacen_id: int) -> Decimal:
    total = db.execute(
        select(func.coalesce(func.sum(Existencia.cantidad_base), 0)).where(
            Existencia.almacen_id == almacen_id
        )
    ).scalar()
    return dec(total or 0)


__all__ = [
    "ErrorNegocio",
    "ErrorStockInsuficiente",
    "ZERO",
    "aplicar_entrada",
    "aplicar_salida",
    "asegurar_existencia",
    "bloquear_existencia",
    "conciliar",
    "existencia_actual",
    "existencias_negativas",
    "registrar_movimiento",
    "saldo_movimientos",
    "stock_total",
]

