"""Reglas de dominio: conversiones de unidades y redondeos (plan §6.1)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.db.models import Dimension

ZERO = Decimal("0")


class ErrorNegocio(Exception):
    """Error de regla de negocio, traducible a una respuesta de API clara."""

    codigo = "error_negocio"
    http_status = 400

    def __init__(self, mensaje: str, *, detalle: dict | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle or {}


class ErrorStockInsuficiente(ErrorNegocio):
    codigo = "stock_insuficiente"
    http_status = 409


class ErrorValidacionUnidad(ErrorNegocio):
    codigo = "unidad_invalida"
    http_status = 400


def q2(value: Decimal) -> Decimal:
    """Redondeo monetario a 2 decimales (half-up)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q4(value: Decimal) -> Decimal:
    """Redondeo de cantidades a 4 decimales."""
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def q6(value: Decimal) -> Decimal:
    """Redondeo de costos unitarios a 6 decimales."""
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def num(value: object) -> str:
    """Serializa un Decimal como cadena sin ceros sobrantes: 120.0000 -> '120'."""
    valor = dec(value)
    texto = format(valor, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto or "0"


def dec(value: object) -> Decimal:
    """Convierte a Decimal sin pasar por float binario."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:  # pragma: no cover - defensivo
        raise ErrorNegocio(f"Valor numérico inválido: {value!r}") from exc


@dataclass(frozen=True)
class Conversion:
    """Resultado de convertir una cantidad de presentación a unidad base."""

    cantidad_presentacion: Decimal
    factor_base: Decimal
    cantidad_base: Decimal
    cantidad_base_sin_redondear: Decimal


def convertir_a_base(
    cantidad: Decimal,
    factor_base: Decimal,
    paso_minimo_base: int,
    *,
    permite_fraccion: bool,
) -> Conversion:
    """Convierte cantidad de presentación a unidad base validando el paso mínimo.

    - Si la presentación no admite fracciones, la cantidad debe ser entera.
    - La cantidad base debe ser múltiplo del paso mínimo de la unidad base.
    """
    if factor_base <= 0:
        raise ErrorValidacionUnidad("El factor de conversión debe ser mayor que cero.")
    if cantidad <= 0:
        raise ErrorNegocio("La cantidad debe ser mayor que cero.")

    if not permite_fraccion and (cantidad % 1) != 0:
        raise ErrorValidacionUnidad(
            "Esta presentación no admite cantidades fraccionadas.",
            detalle={"cantidad": str(cantidad)},
        )

    crudo = cantidad * factor_base
    paso = Decimal(paso_minimo_base or 1)
    redondeado = (crudo / paso).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * paso

    if abs(redondeado - crudo) > (paso / 2):
        raise ErrorValidacionUnidad(
            "La cantidad convertida no respeta el paso mínimo de la unidad base.",
            detalle={
                "cantidad_base_calculada": str(crudo),
                "paso_minimo": str(paso),
            },
        )

    return Conversion(
        cantidad_presentacion=cantidad,
        factor_base=factor_base,
        cantidad_base=redondeado,
        cantidad_base_sin_redondear=crudo,
    )


def formatear_en_unidad_comercial(
    cantidad_base: Decimal, factor_base: Decimal, decimales: int = 3
) -> Decimal:
    """Expresa una cantidad base en la presentación comercial (kg, unidad, etc.)."""
    if factor_base == 0:
        return cantidad_base
    valor = (cantidad_base / factor_base).quantize(
        Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP
    )
    return valor


def es_entero(valor: Decimal) -> bool:
    return (valor % 1) == 0


def paso_por_dimension(dimension: Dimension) -> int:
    """Paso mínimo por dimensión: unidades enteras, gramos, mililitros."""
    return {
        Dimension.UNIDAD: 1,
        Dimension.PESO: 1,
        Dimension.VOLUMEN: 1,
    }[dimension]
