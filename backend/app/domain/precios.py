"""Reglas de precio en la caja (precios variables).

El vendedor puede ajustar el precio de una línea al cerrar la compra, siempre
que el descuento no supere el límite configurado. Si lo supera, la venta se
rechaza con un mensaje claro: solo quien administra precios puede aplicarlo.

Todo se calcula con aritmética decimal exacta.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

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


@dataclass(frozen=True)
class ResultadoPrecioLinea:
    """Resultado de evaluar el precio de una línea completa de la venta.

    En la caja lo que se ajusta es **el total de la línea** («estos 4, cobré
    S/ 8.00»); el precio unitario se deriva de ahí.
    """

    cantidad: Decimal
    precio_original_unitario: Decimal
    total_original: Decimal
    precio_unitario: Decimal
    precio_total: Decimal
    descuento_monto: Decimal
    descuento_porcentaje: Decimal
    permitido: bool
    motivo: str | None = None

    @property
    def hay_cambio(self) -> bool:
        return self.precio_total != self.total_original

    def a_dict(self) -> dict[str, str | bool | None]:
        return {
            "cantidad": str(q4(self.cantidad)),
            "precio_original": str(q2(self.precio_original_unitario)),
            "total_original": str(q2(self.total_original)),
            "precio_unitario": str(q2(self.precio_unitario)),
            "precio_total": str(q2(self.precio_total)),
            "descuento_monto": str(q2(self.descuento_monto)),
            "descuento_porcentaje": str(q4(self.descuento_porcentaje)),
            "permitido": self.permitido,
            "motivo": self.motivo,
        }


def evaluar_precio_linea(
    precio_presentacion: Decimal | str,
    cantidad: Decimal | str,
    *,
    precio_unitario_solicitado: Decimal | str | None = None,
    precio_total_solicitado: Decimal | str | None = None,
    puede_editar_precio: bool,
    puede_administrar_precios: bool,
    limite_porcentaje: Decimal | str = "0",
    limite_monto: Decimal | str = "0",
) -> ResultadoPrecioLinea:
    """Decide el total que se cobra por una línea.

    - Si se indica el **total de la línea**, el precio unitario se deriva de él
      (total ÷ cantidad) y el total cobrado es exactamente el indicado.
    - Si se indica el **precio unitario**, el total es cantidad × precio.
    - El descuento se mide sobre el total de lista (cantidad × precio de lista),
      que es equivalente al descuento por unidad.
    """
    unitario_lista = dec(precio_presentacion)
    cantidad_dec = dec(cantidad)
    total_original = q2(cantidad_dec * unitario_lista)
    limite_pct = dec(limite_porcentaje)
    limite_sol = dec(limite_monto)

    def _sin_cambio(motivo: str | None = None, permitido: bool = True) -> ResultadoPrecioLinea:
        return ResultadoPrecioLinea(
            cantidad=cantidad_dec,
            precio_original_unitario=unitario_lista,
            total_original=total_original,
            precio_unitario=unitario_lista,
            precio_total=total_original,
            descuento_monto=CERO,
            descuento_porcentaje=CERO,
            permitido=permitido,
            motivo=motivo,
        )

    if not puede_editar_precio or (
        precio_total_solicitado is None and precio_unitario_solicitado is None
    ):
        return _sin_cambio()

    if precio_total_solicitado is not None:
        total = q2(dec(precio_total_solicitado))
        if total < 0:
            return _sin_cambio("El total solicitado no puede ser negativo.", permitido=False)
        unitario = (
            (total / cantidad_dec).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            if cantidad_dec != 0
            else unitario_lista
        )
    else:
        unitario = q2(dec(precio_unitario_solicitado))
        total = q2(cantidad_dec * unitario)

    if total > total_original and not puede_administrar_precios:
        return _sin_cambio(
            "El total solicitado es mayor que el de lista: solo un administrador puede aplicarlo.",
            permitido=False,
        )

    descuento = total_original - total
    porcentaje = (descuento / total_original * Decimal("100")) if total_original > 0 else CERO
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
        return ResultadoPrecioLinea(
            cantidad=cantidad_dec,
            precio_original_unitario=unitario_lista,
            total_original=total_original,
            precio_unitario=unitario_lista,
            precio_total=total_original,
            descuento_monto=descuento,
            descuento_porcentaje=porcentaje,
            permitido=False,
            motivo=motivo,
        )

    return ResultadoPrecioLinea(
        cantidad=cantidad_dec,
        precio_original_unitario=unitario_lista,
        total_original=total_original,
        precio_unitario=unitario,
        precio_total=total,
        descuento_monto=descuento,
        descuento_porcentaje=porcentaje,
        permitido=True,
    )


__all__ = ["ResultadoPrecio", "ResultadoPrecioLinea", "evaluar_precio", "evaluar_precio_linea"]
