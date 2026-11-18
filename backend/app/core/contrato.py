"""Contrato de validaciones entre el backend y el cliente.

El backend es la autoridad de las reglas. Este módulo las **extrae de los
schemas** (Pydantic) y las publica en una forma que el cliente puede leer, para
que la interfaz aplique la misma regla y avise antes de enviar.

La idea es que las reglas no se escriban dos veces: viven en el schema, y el
cliente las obtiene de aquí. El test `test_contrato_validaciones.py` verifica
que el contrato está al día y que el cliente lo refleja.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.abastecimientos import AbastecimientoIn, LineaAbastecimientoIn
from app.schemas.auth import LoginRequest, UsuarioCreate, UsuarioUpdate
from app.schemas.catalogo import PresentacionIn, ProductoIn, ProductoUpdate
from app.schemas.configuracion import ConfiguracionIn
from app.schemas.inventario import AjusteIn
from app.schemas.lotes import PrecioLoteIn
from app.schemas.proveedores import ProveedorIn, ProveedorUpdate
from app.schemas.ventas import AnulacionVentaIn, LineaVentaIn, VentaIn

#: Formato del contrato: una regla por dato.
#: `min`/`max` son longitudes (caracteres); `mayor`/`menor_igual` son valores.
Regla = dict[str, Any]


def _restricciones_de_campo(campo: Any) -> Regla:
    """Lee las restricciones que Pydantic puso en un campo."""
    regla: Regla = {}
    for metadato in getattr(campo, "metadata", []) or []:
        tipo = type(metadato).__name__
        if tipo == "MinLen":
            regla["min"] = metadato.min_length
        elif tipo == "MaxLen":
            regla["max"] = metadato.max_length
        elif tipo == "Gt":
            regla["mayor"] = float(metadato.gt)
        elif tipo == "Ge":
            regla["menor_igual"] = float(metadato.ge)
        elif tipo == "Le":
            regla["mayor_igual"] = float(metadato.le)
    return regla


def reglas_de_schema(schema: type[BaseModel]) -> dict[str, Regla]:
    """Extrae las reglas de todos los campos de un schema."""
    reglas: dict[str, Regla] = {}
    for nombre, campo in schema.model_fields.items():
        regla = _restricciones_de_campo(campo)
        if regla:
            reglas[nombre] = regla
    return reglas


#: Reglas que el cliente debe reflejar, por pantalla.
#: El cliente las usa para avisar antes de enviar; el backend sigue mandando.
CONTRATO: dict[str, dict[str, Regla]] = {
    "acceso": reglas_de_schema(LoginRequest),
    "usuarios": reglas_de_schema(UsuarioCreate),
    "usuarios_edicion": reglas_de_schema(UsuarioUpdate),
    "productos": reglas_de_schema(ProductoIn),
    "productos_edicion": reglas_de_schema(ProductoUpdate),
    "presentaciones": reglas_de_schema(PresentacionIn),
    "proveedores": reglas_de_schema(ProveedorIn),
    "proveedores_edicion": reglas_de_schema(ProveedorUpdate),
    "ventas": reglas_de_schema(LineaVentaIn),
    "ventas_cabecera": reglas_de_schema(VentaIn),
    "anulacion_venta": reglas_de_schema(AnulacionVentaIn),
    "abastecimientos": reglas_de_schema(LineaAbastecimientoIn),
    "abastecimientos_documento": reglas_de_schema(AbastecimientoIn),
    "ajustes": reglas_de_schema(AjusteIn),
    "lotes_precio": reglas_de_schema(PrecioLoteIn),
    "configuracion": reglas_de_schema(ConfiguracionIn),
}


def contrato_completo() -> dict[str, Any]:
    """Contrato con las reglas de los schemas y las listas cerradas."""
    from app.domain.pagos import FORMAS_PAGO

    return {
        "reglas": CONTRATO,
        "formas_pago": list(FORMAS_PAGO),
    }
