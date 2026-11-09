"""Importación de catálogo desde Excel/CSV con vista previa (plan §5.1, Fase 4).

El flujo tiene dos pasos obligatorios:
1. `previsualizar` lee el archivo y devuelve el detalle de cada fila sin tocar la base.
2. `confirmar` aplica solo las filas válidas, registrando el resultado por fila.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Almacen, Categoria, Marca, PresentacionProducto, Producto, UnidadMedida
from app.domain.unidades import ErrorNegocio, dec, num
from app.services import catalogo

COLUMNAS = [
    "codigo",
    "nombre",
    "categoria",
    "marca",
    "unidad_base",
    "stock_minimo",
    "presentacion",
    "factor_base",
    "precio_venta",
    "costo_referencia",
    "codigo_barras",
    "permite_fraccion",
    "stock_inicial",
    "costo_inicial",
]

TITULOS = {
    "codigo": "Código",
    "nombre": "Nombre del producto",
    "categoria": "Categoría",
    "marca": "Marca",
    "unidad_base": "Unidad base (UND/GR/ML)",
    "stock_minimo": "Stock mínimo (unidad base)",
    "presentacion": "Presentación de venta",
    "factor_base": "Factor de conversión",
    "precio_venta": "Precio de venta",
    "costo_referencia": "Costo de referencia",
    "codigo_barras": "Código de barras",
    "permite_fraccion": "¿Admite fracción? (SI/NO)",
    "stock_inicial": "Stock inicial (opcional)",
    "costo_inicial": "Costo unitario inicial (opcional)",
}


@dataclass
class FilaImportada:
    numero: int
    codigo: str = ""
    nombre: str = ""
    categoria: str = ""
    marca: str = ""
    unidad_base: str = ""
    stock_minimo: str = ""
    presentacion: str = ""
    factor_base: str = ""
    precio_venta: str = ""
    costo_referencia: str = ""
    codigo_barras: str = ""
    permite_fraccion: str = ""
    stock_inicial: str = ""
    costo_inicial: str = ""
    estado: str = "nuevo"
    mensajes: list[str] = field(default_factory=list)

    @property
    def valida(self) -> bool:
        return not self.mensajes

    def a_dict(self) -> dict[str, Any]:
        return {
            "numero": self.numero,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "presentacion": self.presentacion,
            "factor_base": self.factor_base,
            "precio_venta": self.precio_venta,
            "stock_inicial": self.stock_inicial,
            "estado": self.estado,
            "mensajes": self.mensajes,
        }


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _normalizar_encabezado(texto: str) -> str:
    """Minúsculas, sin acentos ni signos: 'Unidad base (UND/GR/ML)' -> 'unidad base'."""
    limpio = "".join(
        c for c in unicodedata.normalize("NFD", texto.strip().lower())
        if unicodedata.category(c) != "Mn"
    )
    limpio = re.sub(r"[^a-z0-9]+", " ", limpio).strip()
    return limpio


ALIAS_COLUMNAS = {
    "codigo": "codigo",
    "codigo interno": "codigo",
    "cod": "codigo",
    "nombre": "nombre",
    "nombre del producto": "nombre",
    "descripcion": "descripcion",
    "categoria": "categoria",
    "marca": "marca",
    "unidad base": "unidad_base",
    "unidad": "unidad_base",
    "unidad de medida": "unidad_base",
    "stock minimo": "stock_minimo",
    "minimo": "stock_minimo",
    "presentacion": "presentacion",
    "presentacion de venta": "presentacion",
    "presentacion de compra": "presentacion",
    "factor": "factor_base",
    "factor de conversion": "factor_base",
    "precio": "precio_venta",
    "precio de venta": "precio_venta",
    "costo de referencia": "costo_referencia",
    "costo referencia": "costo_referencia",
    "codigo de barras": "codigo_barras",
    "codigo barras": "codigo_barras",
    "permite fraccion": "permite_fraccion",
    "admite fraccion": "permite_fraccion",
    "fraccion": "permite_fraccion",
    "stock inicial": "stock_inicial",
    "costo inicial": "costo_inicial",
    "costo unitario inicial": "costo_inicial",
}


def _resolver_columna(encabezado: str) -> str | None:
    """Traduce el encabezado del archivo al nombre interno de la columna."""
    normalizado = _normalizar_encabezado(encabezado)
    if not normalizado:
        return None
    if normalizado in ALIAS_COLUMNAS:
        return ALIAS_COLUMNAS[normalizado]
    for alias, columna in ALIAS_COLUMNAS.items():
        if normalizado.startswith(alias):
            return columna
    return None


def _es_verdadero(valor: str) -> bool:
    return valor.strip().upper() in {"SI", "SÍ", "X", "1", "TRUE", "VERDADERO"}


def leer_filas(contenido: bytes, nombre_archivo: str = "") -> list[FilaImportada]:
    """Lee el archivo (xlsx o csv) y devuelve las filas crudas."""
    filas: list[FilaImportada] = []
    if nombre_archivo.lower().endswith(".csv") or (
        not nombre_archivo.lower().endswith(".xlsx")
        and not nombre_archivo.lower().endswith(".xlsm")
    ):
        texto = contenido.decode("utf-8-sig", errors="replace")
        lector = csv.DictReader(io.StringIO(texto))
        for indice, registro in enumerate(lector, start=2):
            fila = FilaImportada(numero=indice)
            for clave, valor in registro.items():
                if clave is None:
                    continue
                columna = _resolver_columna(clave)
                if columna in COLUMNAS:
                    setattr(fila, columna, _texto(valor))
            filas.append(fila)
        return filas

    libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    hoja = libro.active
    encabezados: list[str | None] = []
    for indice_fila, valores in enumerate(hoja.iter_rows(values_only=True), start=1):
        if indice_fila == 1:
            encabezados = [_resolver_columna(str(v)) if v is not None else None for v in valores]
            continue
        fila = FilaImportada(numero=indice_fila)
        for indice, valor in enumerate(valores):
            if indice >= len(encabezados):
                break
            columna = encabezados[indice]
            if columna in COLUMNAS:
                setattr(fila, columna, _texto(valor))
        filas.append(fila)
    return filas


def _validar_fila(db: Session, fila: FilaImportada) -> None:
    if not fila.codigo:
        fila.mensajes.append("Falta el código del producto.")
    if not fila.nombre:
        fila.mensajes.append("Falta el nombre del producto.")
    if not fila.unidad_base:
        fila.mensajes.append("Falta la unidad base (UND, GR o ML).")
    else:
        unidad = db.execute(
            select(UnidadMedida).where(
                func.lower(UnidadMedida.codigo) == fila.unidad_base.lower()
            )
        ).scalar_one_or_none()
        if unidad is None:
            fila.mensajes.append(
                f"La unidad base «{fila.unidad_base}» no está registrada (UND, GR, ML)."
            )
    if fila.presentacion:
        if not fila.factor_base:
            fila.mensajes.append("Falta el factor de conversión de la presentación.")
        else:
            try:
                if dec(fila.factor_base) <= 0:
                    fila.mensajes.append("El factor de conversión debe ser mayor que cero.")
            except Exception:
                fila.mensajes.append("El factor de conversión no es un número válido.")
    for campo in ("precio_venta", "costo_referencia", "stock_minimo", "stock_inicial"):
        valor = getattr(fila, campo)
        if valor:
            try:
                dec(valor)
            except Exception:
                fila.mensajes.append(f"El valor de «{campo}» no es numérico.")

    if fila.codigo:
        existente = db.execute(
            select(Producto).where(func.lower(Producto.codigo) == fila.codigo.lower())
        ).scalar_one_or_none()
        fila.estado = "actualizar" if existente is not None else "nuevo"


def previsualizar(db: Session, contenido: bytes, nombre_archivo: str = "") -> dict[str, Any]:
    """Analiza el archivo sin escribir nada en la base de datos."""
    filas = leer_filas(contenido, nombre_archivo)
    for fila in filas:
        if not any(
            getattr(fila, columna)
            for columna in ("codigo", "nombre", "presentacion", "factor_base")
        ):
            continue  # fila vacía
        _validar_fila(db, fila)

    # Duplicados dentro del mismo archivo: un mismo producto puede repetirse en
    # varias filas si cada fila describe una presentación distinta.
    vistos: dict[str, list[int]] = {}
    for fila in filas:
        if not fila.codigo:
            continue
        clave = f"{fila.codigo.lower()}::{fila.presentacion.strip().lower()}"
        vistos.setdefault(clave, []).append(fila.numero)
    for clave, numeros in vistos.items():
        if len(numeros) > 1:
            codigo = clave.split("::")[0]
            presentacion = clave.split("::")[1]
            for fila in filas:
                if fila.codigo.lower() == codigo and fila.presentacion.strip().lower() == presentacion:
                    fila.mensajes.append(
                        f"La combinación código «{fila.codigo}» + presentación "
                        f"«{fila.presentacion}» aparece repetida en las filas {numeros}."
                    )

    validas = [f for f in filas if f.codigo or f.nombre or f.presentacion]
    resumen = {
        "filas": len(validas),
        "nuevos": sum(1 for f in validas if f.estado == "nuevo" and f.valida),
        "actualizar": sum(1 for f in validas if f.estado == "actualizar" and f.valida),
        "con_errores": sum(1 for f in validas if not f.valida),
    }
    return {
        "resumen": resumen,
        "filas": [f.a_dict() for f in validas],
        "detalle": filas,
    }


def _obtener_crear(
    db: Session, modelo, campo_nombre: str, valor: str
):
    if not valor:
        return None
    existente = db.execute(
        select(modelo).where(func.lower(getattr(modelo, campo_nombre)) == valor.lower())
    ).scalar_one_or_none()
    if existente is None:
        existente = modelo(nombre=valor)
        db.add(existente)
        db.flush()
    return existente


def confirmar(
    db: Session,
    contenido: bytes,
    nombre_archivo: str = "",
    *,
    aplicar_stock_inicial: bool = True,
    almacen_id: int | None = None,
    usuario_id: int | None = None,
) -> dict[str, Any]:
    """Aplica las filas válidas y devuelve el resultado por fila."""
    analisis = previsualizar(db, contenido, nombre_archivo)
    filas: list[FilaImportada] = analisis["detalle"]

    aplicadas: list[dict[str, Any]] = []
    rechazadas: list[dict[str, Any]] = []
    importadas = 0
    productos_creados: set[int] = set()
    productos_tocados: set[int] = set()

    # Productos que ya existían antes de la importación (para reportarlos aparte).
    preexistentes = set(db.execute(select(Producto.id)).scalars().all())

    from app.services import inventario

    for fila in filas:
        if not any(
            getattr(fila, columna)
            for columna in ("codigo", "nombre", "presentacion", "factor_base")
        ):
            continue
        if not fila.valida:
            rechazadas.append(fila.a_dict())
            continue

        unidad = db.execute(
            select(UnidadMedida).where(
                func.lower(UnidadMedida.codigo) == fila.unidad_base.lower()
            )
        ).scalar_one()
        categoria = _obtener_crear(db, Categoria, "nombre", fila.categoria)
        marca = _obtener_crear(db, Marca, "nombre", fila.marca)

        producto = db.execute(
            select(Producto).where(func.lower(Producto.codigo) == fila.codigo.lower())
        ).scalar_one_or_none()

        if producto is None:
            producto = catalogo.crear_producto(
                db,
                {
                    "codigo": fila.codigo,
                    "nombre": fila.nombre,
                    "categoria_id": categoria.id if categoria else None,
                    "marca_id": marca.id if marca else None,
                    "unidad_base_id": unidad.id,
                    "stock_minimo_base": fila.stock_minimo or "0",
                    "permite_fraccion": _es_verdadero(fila.permite_fraccion),
                    "activo": True,
                    "presentaciones": [],
                },
            )
            productos_creados.add(producto.id)
        else:
            producto.nombre = fila.nombre or producto.nombre
            producto.nombre_normalizado = catalogo.normalizar(producto.nombre)
            if categoria is not None:
                producto.categoria_id = categoria.id
            if marca is not None:
                producto.marca_id = marca.id
            if fila.stock_minimo:
                producto.stock_minimo_base = dec(fila.stock_minimo)
            productos_tocados.add(producto.id)
            db.flush()

        if fila.presentacion:
            presentacion = db.execute(
                select(PresentacionProducto).where(
                    PresentacionProducto.producto_id == producto.id,
                    func.lower(PresentacionProducto.nombre) == fila.presentacion.lower(),
                )
            ).scalar_one_or_none()
            if presentacion is None:
                presentacion = catalogo.crear_presentacion(
                    db,
                    producto.id,
                    {
                        "nombre": fila.presentacion,
                        "factor_base": fila.factor_base,
                        "precio_venta": fila.precio_venta or "0",
                        "costo_referencia": fila.costo_referencia or "0",
                        "codigo_barras": fila.codigo_barras or None,
                        "permite_fraccion": _es_verdadero(fila.permite_fraccion),
                    },
                )
            else:
                catalogo.actualizar_presentacion(
                    db,
                    presentacion.id,
                    {
                        "factor_base": fila.factor_base,
                        "precio_venta": fila.precio_venta or "0",
                        "costo_referencia": fila.costo_referencia or "0",
                        "codigo_barras": fila.codigo_barras or None,
                        "permite_fraccion": _es_verdadero(fila.permite_fraccion),
                    },
                )

        # --- Stock inicial (carga inicial, no es una compra) --------------
        if aplicar_stock_inicial and fila.stock_inicial:
            cantidad_base = dec(fila.stock_inicial)
            if cantidad_base > 0:
                if almacen_id is None:
                    almacen = db.execute(
                        select(Almacen)
                        .where(Almacen.activo.is_(True))
                        .order_by(Almacen.id)
                    ).scalars().first()
                else:
                    almacen = db.get(Almacen, almacen_id)
                if almacen is None:
                    raise ErrorNegocio("No hay un almacén activo para registrar el stock inicial.")
                costo = dec(fila.costo_inicial or "0")
                inventario.aplicar_entrada(
                    db,
                    almacen_id=almacen.id,
                    producto_id=producto.id,
                    cantidad_base=cantidad_base,
                    costo_unitario_base=costo,
                    tipo="SALDO_INICIAL",
                    origen_tipo="IMPORTACION",
                    origen_id=0,
                    usuario_id=usuario_id,
                    referencia="Importación de catálogo",
                )

        importadas += 1
        aplicadas.append(fila.a_dict())

    return {
        "importadas": importadas,
        "productos_creados": len(productos_creados),
        "productos_actualizados": len(productos_tocados & preexistentes),
        "rechazadas": len(rechazadas),
        "aplicadas": aplicadas,
        "errores": rechazadas,
    }


def plantilla_excel() -> bytes:
    """Genera la plantilla de importación con sus encabezados y un ejemplo."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Catalogo"
    hoja.append([TITULOS[columna] for columna in COLUMNAS])
    hoja.append(
        [
            "P0001",
            "Arroz a granel",
            "Granos y menestras",
            "Genérica",
            "GR",
            "10000",
            "1 kg",
            "1000",
            "5.00",
            "3.40",
            "7750885000001",
            "SI",
            "50000",
            "0.0034",
        ]
    )
    hoja.append(
        [
            "P0001",
            "Arroz a granel",
            "Granos y menestras",
            "Genérica",
            "GR",
            "10000",
            "saco 50 kg",
            "50000",
            "180.00",
            "170.00",
            "",
            "NO",
            "",
            "",
        ]
    )
    hoja.freeze_panes = "A2"
    for indice, columna in enumerate(COLUMNAS, start=1):
        hoja.column_dimensions[hoja.cell(row=1, column=indice).column_letter].width = 24
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


__all__ = ["confirmar", "leer_filas", "previsualizar", "plantilla_excel"]


