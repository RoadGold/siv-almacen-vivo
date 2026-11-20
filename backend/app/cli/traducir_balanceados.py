"""Traduce las listas de distribuidores al modelo del sistema.

Un producto = un alimento (por ejemplo, «Pollos Inicio Premium»).
Una presentación = un empaque concreto (por ejemplo, «saco 40 kg pellet»).

En las listas de VITAMAXPRO el mismo alimento aparece en varias filas porque
viene en distintos empaques («X 40», «X 20», «20X1 KG»). Esos filas se agrupan
en un solo producto con varias presentaciones, que es como se vende de verdad:
el empleado busca el alimento y elige el empaque.

El stock se lleva en gramos (GR).
"""

from __future__ import annotations

import re

from app.cli.datos_balanceados import (
    MARGEN,
    PESO_POR_DEFECTO_KG,
    Item,
    Empaque,
    _CATEGORIAS_TOMASINO,
    _TOMASINO,
    _VITAMAXPRO,
    precio_venta_de,
)

#: Empaque al final del nombre: «X 40», «X40», «20X1 KG», «20x1 KG».
RE_EMPAQUE = re.compile(
    r"\s*(?:X\s*(\d+)\s*(?:KG)?|(\d+)\s*[Xx]\s*1\s*(?:KG)?)\s*$",
    re.IGNORECASE,
)

#: Sufijo del empaque al final de la descripción de TOMASINO: «, 1x40», «, 20 x 1».
RE_SUFIJO_TOMASINO = re.compile(r",?\s*(?:\d+\s*[xX]\s*\d+)\s*$")

#: Formas de presentación que se reconocen en el nombre del producto.
FORMAS_NOMBRE = ("MICROPELLET", "MICRO-PELLET", "HARINA", "PELLET", "POLVO")

#: Palabras que delatan la categoría en TOMASINO, cuando no está en el mapa.
PALABRAS_CATEGORIA: list[tuple[str, str]] = [
    ("cerdo", "Cerdos"),
    ("marrana", "Cerdos"),
    ("chanchilla", "Cerdos"),
    ("lechon", "Cerdos"),
    ("terner", "Vacunos"),
    ("vaca", "Vacunos"),
    ("toro", "Vacunos"),
    ("calf", "Vacunos"),
    ("poll", "Pollos granja"),
    ("broiler", "Pollos granja"),
    ("concen", "Pollos granja"),
    ("layer", "Postura"),
    ("postura", "Postura"),
    ("gallina", "Postura"),
    ("pavo", "Pavos"),
    ("pato", "Patos"),
    ("conejo", "Conejos y cuyes"),
    ("conejina", "Conejos y cuyes"),
    ("cuye", "Conejos y cuyes"),
    ("ovino", "Ovinos"),
    ("caballo", "Caballos"),
    ("equus", "Caballos"),
    ("ave", "Aves"),
    ("avemed", "Aves"),
    ("supervit", "Aves"),
]


def _forma_del_nombre(nombre: str) -> str | None:
    """La forma de presentación que dice el nombre, si la dice al final."""
    limpio = nombre.strip()
    for forma in FORMAS_NOMBRE:
        sufijo = " " + forma
        if limpio.upper().endswith(sufijo):
            return "MICROPELLET" if forma.startswith("MICRO") else forma
    return None


def _detectar_empaque(nombre: str) -> tuple[str, int, int | None]:
    """Separa el empaque del nombre.

    Devuelve (nombre limpio, peso en kg, cantidad de bolsas de 1 kg).
    """
    limpio = nombre.strip()
    peso = PESO_POR_DEFECTO_KG
    bolsas: int | None = None

    coincidencia = RE_EMPAQUE.search(limpio)
    if coincidencia:
        if coincidencia.group(1):
            peso = int(coincidencia.group(1))
            limpio = limpio[: coincidencia.start()].strip()
        else:
            bolsas = int(coincidencia.group(2))
            peso = bolsas
            limpio = limpio[: coincidencia.start()].strip()

    return limpio, peso, bolsas


def _categoria_de_tomasino(codigo: str, nombre: str) -> str:
    """La categoría de un producto de TOMASINO."""
    if codigo in _CATEGORIAS_TOMASINO:
        return _CATEGORIAS_TOMASINO[codigo]
    minusculas = nombre.lower()
    for palabra, categoria in PALABRAS_CATEGORIA:
        if palabra in minusculas:
            return categoria
    return "Otros"


def _limpiar_nombre(nombre: str, forma_ignorada: str | None) -> str:
    """Quita del final del nombre la forma, si ya viene de las columnas."""
    limpio = nombre.strip()
    if forma_ignorada:
        sufijo = " " + forma_ignorada
        if limpio.upper().endswith(sufijo):
            limpio = limpio[: -len(sufijo)].strip()
    return limpio


def _nombre_limpio_de_forma(nombre: str) -> tuple[str, str | None]:
    """Quita la forma del final del nombre y la devuelve.

    «POLLOS ENGORDE PREMIUN POLVO» -> («POLLOS ENGORDE PREMIUN», «POLVO»)
    «AVEPROMICINA X 40 MICROPELLET» -> («AVEPROMICINA X 40», «MICROPELLET»)
    """
    limpio = nombre.strip()
    for forma in FORMAS_NOMBRE:
        sufijo = " " + forma
        if limpio.upper().endswith(sufijo):
            normalizada = "MICROPELLET" if forma.startswith("MICRO") else forma
            return limpio[: -len(sufijo)].strip(), normalizada
    return limpio, None


def _forma_en_el_nombre(nombre: str) -> str | None:
    """La forma que dice el nombre, esté donde esté.

    «CUYES CARNE POLVO PER-S» -> «POLVO» (aunque el precio viniera en la
    columna de pellet: manda el nombre, que es lo que se busca en la caja).
    """
    partes = nombre.upper().split()
    for forma in FORMAS_NOMBRE:
        for parte in partes:
            if parte.strip(",.") == forma:
                return "MICROPELLET" if forma.startswith("MICRO") else forma
    return None


def _separar_empaque_y_forma(nombre: str) -> tuple[str, int, int | None, str | None]:
    """Separa el nombre en (nombre, peso, bolsas, forma).

    El empaque («X 40») y la forma («POLVO») pueden venir en cualquier orden al
    final del nombre, así que se van quitando hasta que no quede ninguno.
    """
    limpio = nombre.strip()
    peso = PESO_POR_DEFECTO_KG
    bolsas: int | None = None
    forma: str | None = None

    for _ in range(4):
        cambio = False

        sin_forma, forma_final = _nombre_limpio_de_forma(limpio)
        if forma_final is not None:
            limpio = sin_forma
            forma = forma_final
            cambio = True

        coincidencia = RE_EMPAQUE.search(limpio)
        if coincidencia:
            if coincidencia.group(1):
                peso = int(coincidencia.group(1))
            else:
                bolsas = int(coincidencia.group(2))
                peso = bolsas
            limpio = limpio[: coincidencia.start()].strip()
            cambio = True

        if not cambio:
            break

    if forma is None:
        forma = _forma_en_el_nombre(limpio)

    return limpio, peso, bolsas, forma


def items_vitamaxpro() -> list[Item]:
    """Los productos de VITAMAXPRO e INVITA, agrupados por alimento.

    El mismo alimento en distintos empaques se convierte en un solo producto
    con varias presentaciones. Los códigos se asignan al final, sobre los
    productos ya agrupados, para que sean consecutivos.
    """
    # --- Se agrupan por (marca, nombre del alimento) ---------------------
    grupos: dict[tuple[str, str], dict] = {}

    for linea, nombre_completo, pellet, polvo, nota in _VITAMAXPRO:
        # Se separan el empaque y la forma del nombre.
        limpio, peso, bolsas, forma_nombre = _separar_empaque_y_forma(nombre_completo)

        if limpio.startswith("VITAMAXPRO"):
            marca = "Vitamaxpro"
            nombre = limpio[len("VITAMAXPRO") :].strip()
        else:
            marca = "Invita"
            nombre = limpio[len("INVITA") :].strip()

        # Si el nombre dice la forma y la columna del precio dice otra, gana
        # el nombre: es lo que el empleado busca en la caja.
        clave = (marca, nombre)
        grupo = grupos.setdefault(
            clave,
            {
                "linea": linea,
                "nombre": nombre,
                "marca": marca,
                "empaques": {},
                "notas": [],
            },
        )

        for forma_columna, precio in (("PELLET", pellet), ("POLVO", polvo)):
            if precio == "-":
                continue
            forma = forma_nombre or forma_columna
            empaque = Empaque(
                forma=forma, peso_kg=peso, precio_costo=precio, bolsas=bolsas
            )
            if empaque.nombre in grupo["empaques"]:
                # Mismo empaque dos veces: se queda el primero.
                continue
            grupo["empaques"][empaque.nombre] = empaque
        if nota:
            grupo["notas"].append(nota)

    # --- Se arman los productos ------------------------------------------
    # El código NO se fija aquí: lo asigna la carga, que busca el producto por
    # su nombre (marca + nombre) y le conserva el código que ya tiene. Así, si
    # la lista de precios crece o cambia el orden, ningún producto cambia de
    # código y no se rompe el historial.
    items: list[Item] = []
    for (marca, nombre), grupo in grupos.items():
        # Las formas se ordenan por peso para que la lista sea estable.
        empaques = sorted(
            grupo["empaques"].values(), key=lambda e: (e.peso_kg, e.forma)
        )
        notas = list(dict.fromkeys(grupo["notas"]))
        items.append(
            Item(
                proveedor="VITAMAXPRO",
                categoria=grupo["linea"],
                marca=marca,
                nombre=nombre,
                codigo="",
                empaques=empaques,
                nota=" · ".join(notas),
                empaque_de_compra=empaques[0].nombre if empaques else None,
            )
        )

    # Se ordenan por nombre para que la carga sea siempre la misma.
    items.sort(key=lambda item: (item.marca, item.nombre))

    return items


def items_tomasino() -> list[Item]:
    """Los productos de TOMASINO.

    Cada código del distribuidor es un producto distinto: así se puede pedir
    y facturar por el código que viene en la lista.
    """
    items: list[Item] = []
    codigos_sin_codigo = 0

    for codigo, forma, peso, descripcion, precio, nota in _TOMASINO:
        nombre = RE_SUFIJO_TOMASINO.sub("", descripcion).strip()

        # «20 x 1» son 20 bolsas de 1 kilo; el empaque es de 20 kg.
        bolsas = None
        coincidencia = re.search(r"(\d+)\s*x\s*1\b", descripcion, re.IGNORECASE)
        if coincidencia:
            bolsas = int(coincidencia.group(1))

        peso_kg = int(peso)
        if bolsas and not peso_kg:
            peso_kg = bolsas

        if codigo == "S/C":
            codigos_sin_codigo += 1
            codigo_producto = f"TOM-SC-{codigos_sin_codigo:02d}"
        else:
            codigo_producto = codigo

        empaque = Empaque(
            forma=forma, peso_kg=peso_kg, precio_costo=precio, bolsas=bolsas
        )
        items.append(
            Item(
                proveedor="TOMASINO",
                categoria=_categoria_de_tomasino(codigo, nombre),
                marca="Tomasino",
                nombre=nombre,
                codigo=codigo_producto,
                empaques=[empaque],
                nota=nota,
                empaque_de_compra=empaque.nombre,
            )
        )

    return items


def todos_los_items() -> list[Item]:
    """Todo el catálogo inicial, en orden."""
    return items_vitamaxpro() + items_tomasino()


__all__ = [
    "MARGEN",
    "Empaque",
    "Item",
    "items_tomasino",
    "items_vitamaxpro",
    "precio_venta_de",
    "todos_los_items",
]
