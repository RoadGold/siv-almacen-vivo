"""Costo promedio ponderado móvil (plan §6.2)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.unidades import ZERO, q6


def costo_promedio_tras_entrada(
    cantidad_previa: Decimal,
    costo_previo: Decimal,
    cantidad_entrada: Decimal,
    costo_entrada_unitario: Decimal,
) -> Decimal:
    """Costo medio nuevo tras una entrada.

        C_nuevo = (Q_previo*C_previo + Q_entrada*C_entrada) / (Q_previo + Q_entrada)

    Si el stock previo es cero, el costo medio inicial es el de la entrada.
    """
    if cantidad_previa < 0 or cantidad_entrada < 0:
        raise ValueError("Las cantidades no pueden ser negativas.")
    if cantidad_previa == 0:
        return q6(costo_entrada_unitario)
    total_q = cantidad_previa + cantidad_entrada
    if total_q == 0:
        return ZERO
    return q6(
        (cantidad_previa * costo_previo + cantidad_entrada * costo_entrada_unitario) / total_q
    )


def costo_promedio_tras_salida(
    cantidad_previa: Decimal,
    costo_previo: Decimal,
    cantidad_salida: Decimal,
    costo_salida_unitario: Decimal,
) -> Decimal:
    """Costo medio tras una salida: se retira del valor con el costo aplicado."""
    if cantidad_previa == 0:
        return ZERO
    restante = cantidad_previa - cantidad_salida
    if restante <= 0:
        # La salida consumió todo el stock: el costo promedio deja de existir.
        return ZERO
    valor = cantidad_previa * costo_previo - cantidad_salida * costo_salida_unitario
    return q6(valor / restante)
