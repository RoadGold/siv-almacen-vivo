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


def q2(value: object) -> Decimal:
    """Redondeo monetario a 2 decimales (half-up)."""
    return dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q4(value: object) -> Decimal:
    """Redondeo de cantidades a 4 decimales."""
    return dec(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def q6(value: object) -> Decimal:
    """Redondeo de costos unitarios a 6 decimales."""
    return dec(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


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


def _normalizar_miles(texto: str) -> str:
    """Entiende la notación de miles que usa la persona al escribir.

    Reglas acordadas con el negocio:
      1.000  ·  1 000  ·  1,000   ->  1000   (miles)
      1.234,56                   ->  1234.56 (miles y decimal)
      12,50  ·  0,750            ->  12.50  ·  0.750 (decimal)
      1.5                        ->  1.5    (decimal)

    La interfaz ya normaliza antes de enviar, pero el backend también lo hace:
    así una importación directa o un cliente viejo no vuelve a registrar
    «1.000» como 1.
    """
    limpio = texto.replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
    if limpio == "":
        return limpio

    tiene_coma = "," in limpio
    tiene_punto = "." in limpio

    if tiene_coma and tiene_punto:
        # 1.234,56 -> el punto es de miles y la coma es decimal.
        limpio = limpio.replace(".", "").replace(",", ".")
    elif tiene_coma:
        entero, _, decimales = limpio.partition(",")
        if len(decimales) == 3 and 1 <= len(entero) <= 3 and entero != "0":
            # 1,000 -> miles (tres decimales y parte entera de 1 a 3).
            limpio = entero + decimales
        else:
            limpio = f"{entero}.{decimales}"
    elif tiene_punto:
        partes = limpio.split(".")
        decimales = partes[1:]
        if (
            len(partes) > 1
            and all(len(parte) == 3 for parte in decimales)
            and 1 <= len(partes[0]) <= 3
            and partes[0] != "0"
        ):
            # 1.000 -> miles ; 1.234.567 -> millones.
            limpio = "".join(partes)

    return limpio


def decimal_ingreso(valor: object) -> Decimal:
    """Como `dec`, pero para lo que escribe una persona.

    Entiende la notación de miles y el error sale en español y sin detalles
    técnicos: la interfaz lo muestra tal cual bajo el campo.
    """
    if isinstance(valor, Decimal):
        return valor
    if valor is None:
        raise ValueError("no tiene un valor numérico")
    texto = str(valor).strip()
    if texto == "":
        raise ValueError("no tiene un valor numérico")
    try:
        return Decimal(_normalizar_miles(texto))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("no tiene un valor numérico") from error


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
