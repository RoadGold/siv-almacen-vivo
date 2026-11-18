"""Formas de pago admitidas en la caja.

La lista es cerrada: el backend solo acepta estas formas y el frontend ofrece
exactamente las mismas. Así no se puede registrar una venta con una forma de
pago inventada (por ejemplo, un cobro a crédito que nadie autorizó).
"""

from __future__ import annotations

from enum import StrEnum


class FormaPago(StrEnum):
    """Formas de pago con las que se puede cerrar una venta."""

    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    VOUCHER = "voucher"
    YAPE = "yape"


#: Formas de pago que ofrecen la caja, en el orden en que se muestran.
FORMAS_PAGO: tuple[str, ...] = tuple(forma.value for forma in FormaPago)

#: Texto que se muestra en el ticket y en la venta.
ETIQUETAS_FORMA_PAGO: dict[str, str] = {
    FormaPago.EFECTIVO: "Efectivo",
    FormaPago.TARJETA: "Tarjeta",
    FormaPago.VOUCHER: "Voucher",
    FormaPago.YAPE: "Yape / Plin",
}


def es_forma_valida(valor: str | None) -> bool:
    """Indica si el texto es una de las formas de pago admitidas."""
    if valor is None:
        return False
    return valor.strip().lower() in FORMAS_PAGO
