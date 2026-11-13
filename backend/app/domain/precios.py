"""Reglas de precio en la caja (precios variables).

El vendedor puede ajustar el precio de una línea al cerrar la compra, siempre
que el descuento no supere el límite configurado. Si lo supera, la venta se
rechaza con un mensaje claro: solo quien administra precios puede aplicarlo.

Todo se calcula con aritmética decimal exacta.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.unidades import dec, q2, q4

CERO = Decimal("0")


@dataclass(frozen=True)
class ResultadoPrecio:
    """Resultado de evaluar el precio solicitado de una línea."""

    precio_original: Decimal
    precio_aplicado: Decimal
    descuento_monto: Decimal
    descuento_porcentaje: Decimal
    permitido: bool
    motivo: str | None = None

    @property
    def hay_cambio(self) -> bool:
        return self.precio_aplicado != self.precio_original

    def a_dict(self) -> dict[str, str | bool | None]:
        return {
            "precio_original": str(q2(self.precio_original)),
            "precio_aplicado": str(q2(self.precio_aplicado)),
            "descuento_monto": str(q2(self.descuento_monto)),
            "descuento_porcentaje": str(q4(self.descuento_porcentaje)),
            "permitido": self.permitido,
            "motivo": self.motivo,
        }


def evaluar_precio(
    precio_presentacion: Decimal | str,
    precio_solicitado: Decimal | str | None,
    *,
    puede_editar_precio: bool,
    puede_administrar_precios: bool,
    limite_porcentaje: Decimal | str = "0",
    limite_monto: Decimal | str = "0",
) -> ResultadoPrecio:
    """Decide el precio final de una línea.

    - Sin precio solicitado o sin permiso para editar: se cobra el precio de lista.
    - Con precio dentro del límite: se cobra el precio solicitado.
    - Por encima del límite: solo se acepta si quien opera administra precios.
    """
    original = dec(precio_presentacion)
    limite_pct = dec(limite_porcentaje)
    limite_sol = dec(limite_monto)

    if precio_solicitado is None or not puede_editar_precio:
        return ResultadoPrecio(
            precio_original=original,
            precio_aplicado=original,
            descuento_monto=CERO,
            descuento_porcentaje=CERO,
            permitido=True,
        )

    solicitado = dec(precio_solicitado)
    if solicitado < 0:
        return ResultadoPrecio(
            precio_original=original,
            precio_aplicado=original,
            descuento_monto=CERO,
            descuento_porcentaje=CERO,
            permitido=False,
            motivo="El precio solicitado no puede ser negativo.",
        )

    if solicitado > original:
        # Subir el precio de lista es una decisión del negocio: solo la
        # administra quien tiene el permiso de precios.
        if not puede_administrar_precios:
            return ResultadoPrecio(
                precio_original=original,
                precio_aplicado=original,
                descuento_monto=CERO,
                descuento_porcentaje=CERO,
                permitido=False,
                motivo=(
                    "El precio solicitado es mayor que el de lista: solo un administrador "
                    "puede aplicarlo."
                ),
            )
        return ResultadoPrecio(
            precio_original=original,
            precio_aplicado=solicitado,
            descuento_monto=CERO,
            descuento_porcentaje=CERO,
            permitido=True,
        )

    descuento = original - solicitado
    porcentaje = (descuento / original * Decimal("100")) if original > 0 else CERO
    excede_porcentaje = limite_pct > 0 and porcentaje > limite_pct
    excede_monto = limite_sol > 0 and descuento > limite_sol

    if (excede_porcentaje or excede_monto) and not puede_administrar_precios:
        motivo = (
            f"El descuento de {q2(porcentaje)} % supera el límite permitido "
            f"({q2(limite_pct)} %)."
            if excede_porcentaje
            else f"El descuento de S/ {q2(descuento)} supera el máximo permitido "
            f"(S/ {q2(limite_sol)})."
        )
        return ResultadoPrecio(
            precio_original=original,
            precio_aplicado=original,
            descuento_monto=descuento,
            descuento_porcentaje=porcentaje,
            permitido=False,
            motivo=motivo,
        )

    return ResultadoPrecio(
        precio_original=original,
        precio_aplicado=solicitado,
        descuento_monto=descuento,
        descuento_porcentaje=porcentaje,
        permitido=True,
    )


__all__ = ["ResultadoPrecio", "evaluar_precio"]
