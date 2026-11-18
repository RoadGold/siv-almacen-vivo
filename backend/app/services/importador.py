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

from app.db.models import (
    Almacen,
    Categoria,
    Existencia,
    Marca,
    PresentacionProducto,
    Producto,
    ProductoProveedor,
    Proveedor,
    UnidadMedida,
)
from app.domain.unidades import ErrorNegocio, dec, num
from app.schemas.catalogo import ProductoIn
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
    "proveedor_codigo",
    "proveedor_habitual",
    "presentacion_compra",
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
    "proveedor_codigo": "Código del proveedor (opcional)",
    "proveedor_habitual": "¿Proveedor habitual? (SI/NO)",
    "presentacion_compra": "Presentación de compra (opcional)",
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
    proveedor_codigo: str = ""
    proveedor_habitual: str = ""
    presentacion_compra: str = ""
    estado: str = "nuevo"
    mensajes: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

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
            "proveedor_codigo": self.proveedor_codigo,
            "estado": self.estado,
            "mensajes": self.mensajes,
            "avisos": self.avisos,
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
    "proveedor": "proveedor_codigo",
    "codigo del proveedor": "proveedor_codigo",
    "proveedor codigo": "proveedor_codigo",
    "proveedor habitual": "proveedor_habitual",
    "habitual": "proveedor_habitual",
    "presentacion de compra": "presentacion_compra",
    "compra": "presentacion_compra",
}


def _resolver_columna(encabezado: str) -> str | None:
    """Traduce el encabezado del archivo al nombre interno de la columna.

    Primero busca una coincidencia exacta y, si no hay, un prefijo. Los alias
    se prueban **del más largo al más corto** para que «Código del proveedor» no
    se confunda con «Código».
    """
    normalizado = _normalizar_encabezado(encabezado)
    if not normalizado:
        return None
    if normalizado in ALIAS_COLUMNAS:
        return ALIAS_COLUMNAS[normalizado]
    for alias in sorted(ALIAS_COLUMNAS, key=len, reverse=True):
        if normalizado.startswith(alias):
            return ALIAS_COLUMNAS[alias]
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
    elif len(fila.codigo) > 40:
        fila.mensajes.append("El código del producto no puede pasar de 40 caracteres.")
    if not fila.nombre:
        fila.mensajes.append("Falta el nombre del producto.")
    elif len(fila.nombre) > 200:
        fila.mensajes.append("El nombre del producto no puede pasar de 200 caracteres.")
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
                numero = dec(valor)
            except Exception:
                fila.mensajes.append(f"El valor de «{campo}» no es numérico.")
                continue
            if numero < 0:
                fila.mensajes.append(f"El valor de «{campo}» no puede ser negativo.")
    if fila.costo_inicial:
        try:
            if dec(fila.costo_inicial) < 0:
                fila.mensajes.append("El valor de «costo_inicial» no puede ser negativo.")
        except Exception:
            fila.mensajes.append("El valor de «costo_inicial» no es numérico.")

    if fila.codigo:
        existente = db.execute(
            select(Producto).where(func.lower(Producto.codigo) == fila.codigo.lower())
        ).scalar_one_or_none()
        fila.estado = "actualizar" if existente is not None else "nuevo"

    # --- Proveedor (opcional) --------------------------------------------
    if fila.proveedor_codigo:
        proveedor = db.execute(
            select(Proveedor).where(
                func.lower(Proveedor.codigo) == fila.proveedor_codigo.lower()
            )
        ).scalar_one_or_none()
        if proveedor is None:
            # No es un error: el producto se importa igual y el vínculo se
            # podrá crear más adelante (el proveedor es opcional).
            fila.avisos.append(
                f"El proveedor «{fila.proveedor_codigo}» no está registrado: el producto se "
                "importa, pero el vínculo no se creará. Cree el proveedor y vuelva a "
                "importar el archivo para vincularlo."
            )
    elif fila.proveedor_habitual:
        fila.avisos.append(
            "Se marcó como proveedor habitual pero no se indicó el código del proveedor: se ignorará."
        )

    if fila.presentacion_compra and not fila.proveedor_codigo:
        fila.avisos.append(
            "Se indicó presentación de compra sin proveedor: se ignorará."
        )


def _detectar_duplicados_por_nombre(db: Session, filas: list[FilaImportada]) -> None:
    """Avisa de posibles productos gemelos: mismo nombre, distinto código."""
    for fila in filas:
        if not fila.nombre:
            continue
        nombre = catalogo.normalizar(fila.nombre)
        # Puede haber más de un producto con el mismo nombre: se listan todos.
        existentes = db.execute(
            select(Producto).where(Producto.nombre_normalizado == nombre)
        ).scalars().all()
        otros = [
            producto
            for producto in existentes
            if not fila.codigo or producto.codigo.lower() != fila.codigo.lower()
        ]
        if otros:
            codigos = ", ".join(producto.codigo for producto in otros[:5])
            fila.avisos.append(
                f"Ya existe un producto con el nombre «{fila.nombre}» "
                f"(código {codigos}). Revise que no sea el mismo artículo."
            )

    por_nombre: dict[str, list[FilaImportada]] = {}
    for fila in filas:
        if fila.nombre:
            por_nombre.setdefault(catalogo.normalizar(fila.nombre), []).append(fila)

    for grupo in por_nombre.values():
        codigos = {f.codigo.lower() for f in grupo if f.codigo}
        if len(codigos) <= 1:
            continue
        for fila in grupo:
            otros = [
                g
                for g in grupo
                if g is not fila and g.codigo and g.codigo.lower() != fila.codigo.lower()
            ]
            if otros:
                filas_otras = ", ".join(str(g.numero) for g in otros)
                fila.avisos.append(
                    f"En el archivo hay otro producto con el mismo nombre (fila {filas_otras})."
                )


def _analizar_stock_inicial(
    db: Session, filas: list[FilaImportada]
) -> dict[str, str]:
    """Decide el stock inicial que se aplicará a cada producto.

    Reglas:
    - Se aplica **una sola vez por producto**, aunque el producto tenga varias
      filas (una por presentación).
    - Si el producto ya tiene existencias registradas, **no** se aplica: se
      avisa para que el usuario use un ajuste si necesita corregirlo.

    Devuelve el mapa código de producto -> cantidad a aplicar.
    """
    grupos: dict[str, list[FilaImportada]] = {}
    for fila in filas:
        if fila.codigo:
            grupos.setdefault(fila.codigo.lower(), []).append(fila)

    por_aplicar: dict[str, str] = {}

    for clave, grupo in grupos.items():
        con_stock = [f for f in grupo if f.stock_inicial]
        if not con_stock:
            continue
        primera = con_stock[0]
        por_aplicar[clave] = primera.stock_inicial

        if len(con_stock) > 1:
            numeros = ", ".join(str(f.numero) for f in con_stock)
            valores = {f.stock_inicial for f in con_stock}
            if len(valores) == 1:
                aviso = (
                    f"El stock inicial se repite en las filas {numeros}: "
                    f"se aplicará una sola vez ({primera.stock_inicial} en unidad base)."
                )
            else:
                aviso = (
                    f"Las filas {numeros} tienen valores de stock inicial distintos: "
                    f"se aplicará el de la fila {primera.numero} ({primera.stock_inicial})."
                )
            for fila in grupo:
                fila.avisos.append(aviso)

        producto = db.execute(
            select(Producto).where(func.lower(Producto.codigo) == primera.codigo.lower())
        ).scalar_one_or_none()
        if producto is not None:
            existencia = db.execute(
                select(Existencia).where(Existencia.producto_id == producto.id)
            ).scalar_one_or_none()
            if existencia is not None:
                por_aplicar.pop(clave, None)
                aviso = (
                    "El producto ya tiene existencias registradas: no se aplicará el stock "
                    "inicial del archivo. Si necesita corregirlo, use un ajuste de inventario."
                )
                for fila in grupo:
                    fila.avisos.append(aviso)

    return por_aplicar


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

    _detectar_duplicados_por_nombre(db, validas)
    stock_por_producto = _analizar_stock_inicial(db, validas)

    resumen = {
        "filas": len(validas),
        "nuevos": sum(1 for f in validas if f.estado == "nuevo" and f.valida),
        "actualizar": sum(1 for f in validas if f.estado == "actualizar" and f.valida),
        "con_errores": sum(1 for f in validas if not f.valida),
        "con_avisos": sum(1 for f in validas if f.avisos),
        "con_stock_inicial": len(stock_por_producto),
        # Solo se cuentan los vínculos que de verdad se van a crear.
        "vinculos_proveedor": sum(
            1
            for f in validas
            if f.proveedor_codigo
            and f.valida
            and not any("no está registrado" in aviso for aviso in f.avisos)
        ),
    }
    return {
        "resumen": resumen,
        "filas": [f.a_dict() for f in validas],
        "detalle": filas,
        "stock_por_producto": stock_por_producto,
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
    productos_con_stock: set[int] = set()
    vinculos_creados = 0
    stock_inicial_aplicado = 0

    # Productos que ya existían antes de la importación (para reportarlos aparte).
    preexistentes = set(db.execute(select(Producto.id)).scalars().all())

    from app.services import inventario

    # Stock inicial que se aplicará, ya depurado por el análisis previo.
    stock_por_producto: dict[str, str] = analisis["stock_por_producto"]

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
            # Se construye el schema real del producto: así la importación
            # hereda las mismas reglas que el alta manual (longitudes, stock
            # mínimo no negativo, factor mayor que cero).
            datos_producto = ProductoIn(
                codigo=fila.codigo,
                nombre=fila.nombre,
                categoria_id=categoria.id if categoria else None,
                marca_id=marca.id if marca else None,
                unidad_base_id=unidad.id,
                stock_minimo_base=fila.stock_minimo or "0",
                permite_fraccion=_es_verdadero(fila.permite_fraccion),
                activo=True,
                presentaciones=[],
            )
            producto = catalogo.crear_producto(db, datos_producto.model_dump())
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

        # --- Vínculo con el proveedor (opcional) --------------------------
        if fila.proveedor_codigo:
            proveedor = db.execute(
                select(Proveedor).where(
                    func.lower(Proveedor.codigo) == fila.proveedor_codigo.lower()
                )
            ).scalar_one_or_none()
            if proveedor is not None:
                presentacion_compra = None
                if fila.presentacion_compra:
                    presentacion_compra = db.execute(
                        select(PresentacionProducto).where(
                            PresentacionProducto.producto_id == producto.id,
                            func.lower(PresentacionProducto.nombre)
                            == fila.presentacion_compra.lower(),
                        )
                    ).scalar_one_or_none()
                    if presentacion_compra is None:
                        fila.avisos.append(
                            f"La presentación de compra «{fila.presentacion_compra}» no existe en "
                            "este producto: el vínculo se guardará sin ella."
                        )
                vinculo = db.execute(
                    select(ProductoProveedor).where(
                        ProductoProveedor.producto_id == producto.id,
                        ProductoProveedor.proveedor_id == proveedor.id,
                    )
                ).scalar_one_or_none()
                if vinculo is None:
                    vinculo = ProductoProveedor(
                        producto_id=producto.id,
                        proveedor_id=proveedor.id,
                        habitual=_es_verdadero(fila.proveedor_habitual),
                        presentacion_id=presentacion_compra.id if presentacion_compra else None,
                    )
                    db.add(vinculo)
                else:
                    vinculo.habitual = _es_verdadero(fila.proveedor_habitual)
                    if presentacion_compra is not None:
                        vinculo.presentacion_id = presentacion_compra.id
                db.flush()
                vinculos_creados += 1

        # --- Stock inicial (carga inicial, no es una compra) --------------
        # Se aplica una sola vez por producto y solo si el producto no tiene
        # existencias registradas (ver _analizar_stock_inicial).
        stock_a_aplicar = stock_por_producto.get(fila.codigo.lower())
        es_la_primera_fila_del_producto = (
            stock_a_aplicar is not None and producto.id not in productos_con_stock
        )
        if aplicar_stock_inicial and stock_a_aplicar and es_la_primera_fila_del_producto:
            productos_con_stock.add(producto.id)
            cantidad_base = dec(stock_a_aplicar)
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
                stock_inicial_aplicado += 1

        importadas += 1
        aplicadas.append(fila.a_dict())

    return {
        "importadas": importadas,
        "productos_creados": len(productos_creados),
        "productos_actualizados": len(productos_tocados & preexistentes),
        "rechazadas": len(rechazadas),
        "vinculos_proveedor": vinculos_creados,
        "stock_inicial_aplicado": stock_inicial_aplicado,
        "aplicadas": aplicadas,
        "errores": rechazadas,
    }


def plantilla_excel() -> bytes:
    """Genera la plantilla de importación con sus encabezados y un ejemplo."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Catalogo"
    hoja.append([TITULOS[columna] for columna in COLUMNAS])

    # Ejemplo 1: producto con proveedor conocido.
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
            "PRV-001",
            "SI",
            "saco 50 kg",
        ]
    )
    # Ejemplo 2: segunda presentación del mismo producto (el stock inicial se
    # escribe solo en la primera fila: se aplica una vez por producto).
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
            "PRV-001",
            "SI",
            "saco 50 kg",
        ]
    )
    # Ejemplo 3: producto del que todavía no se conoce el proveedor.
    hoja.append(
        [
            "P0002",
            "Gaseosa 500 ml",
            "Bebidas",
            "Genérica",
            "UND",
            "48",
            "botella",
            "1",
            "2.50",
            "1.90",
            "7750885000018",
            "NO",
            "72",
            "1.90",
            "",
            "",
            "",
        ]
    )

    hoja.freeze_panes = "A2"
    for indice, columna in enumerate(COLUMNAS, start=1):
        hoja.column_dimensions[hoja.cell(row=1, column=indice).column_letter].width = 24

    # Hoja de ayuda: qué significa cada columna.
    ayuda = libro.create_sheet("Ayuda")
    ayuda.append(["Columna", "Qué escribir"])
    instrucciones = [
        ("Código", "Código interno del producto. No puede repetirse."),
        ("Nombre del producto", "Nombre comercial."),
        ("Categoría", "Se crea si no existe."),
        ("Marca", "Se crea si no existe."),
        ("Unidad base (UND/GR/ML)", "Unidad en la que se acumula el stock: UND, GR o ML."),
        ("Stock mínimo (unidad base)", "Aviso de reposición, en unidad base."),
        ("Presentación de venta", "Una fila por presentación (botella, caja x24, kilo…)."),
        ("Factor de conversión", "Cuántas unidades base tiene la presentación (caja x24 = 24)."),
        ("Precio de venta", "Precio de esa presentación."),
        ("Costo de referencia", "Costo aproximado de compra."),
        ("Código de barras", "Opcional. No puede repetirse."),
        ("¿Admite fracción? (SI/NO)", "SI si el producto se puede vender a medias."),
        (
            "Stock inicial (opcional)",
            "Cantidad inicial EN UNIDAD BASE (no en cajas). Se aplica una sola vez por "
            "producto y solo si el producto todavía no tiene existencias.",
        ),
        (
            "Costo unitario inicial (opcional)",
            "Costo por unidad base del stock inicial (por ejemplo 0.0034 por gramo).",
        ),
        ("Código del proveedor (opcional)", "Puede quedar vacío si todavía no conoce el proveedor."),
        ("¿Proveedor habitual? (SI/NO)", "Si el producto se pide normalmente a ese proveedor."),
        ("Presentación de compra (opcional)", "Presentación con la que compra ese proveedor."),
    ]
    for columna, texto in instrucciones:
        ayuda.append([columna, texto])
    ayuda.column_dimensions["A"].width = 38
    ayuda.column_dimensions["B"].width = 90
    ayuda.freeze_panes = "A2"

    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


__all__ = ["confirmar", "leer_filas", "previsualizar", "plantilla_excel"]


