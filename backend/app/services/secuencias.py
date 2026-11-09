"""Numeración de comprobantes internos (secuencias por tipo y almacén)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import Secuencia

PREFIJOS = {
    "VENTA": "V",
    "ABASTECIMIENTO": "A",
    "AJUSTE": "AJ",
}


def siguiente_numero(db: Session, tipo: str, almacen_id: int | None = None) -> str:
    """Reserva el siguiente número de forma segura dentro de la transacción actual."""
    clave_almacen = almacen_id or 0
    stmt = (
        pg_insert(Secuencia)
        .values(tipo=tipo, almacen_id=clave_almacen, valor=1)
        .on_conflict_do_update(
            index_elements=["tipo", "almacen_id"],
            set_={"valor": Secuencia.valor + 1},
        )
    )
    db.execute(stmt)
    db.flush()
    valor = db.execute(
        select(Secuencia.valor)
        .where(Secuencia.tipo == tipo, Secuencia.almacen_id == clave_almacen)
        .with_for_update()
    ).scalar_one()
    prefijo = PREFIJOS.get(tipo, tipo[:2].upper())
    return f"{prefijo}-{valor:06d}"
