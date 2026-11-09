"""Registro de auditoría de acciones sensibles."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Auditoria


def registrar(
    db: Session,
    *,
    accion: str,
    entidad: str,
    entidad_id: int | None = None,
    actor_id: int | None = None,
    detalle: dict[str, Any] | None = None,
) -> Auditoria:
    registro = Auditoria(
        actor_id=actor_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=json.dumps(detalle, ensure_ascii=False, default=str) if detalle else None,
    )
    db.add(registro)
    db.flush()
    return registro
