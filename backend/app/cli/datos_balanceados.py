"""Catálogo inicial de balanceados (VITAMAXPRO/INVITA y TOMASINO).

Contiene las dos listas de precios de distribuidor que pasó el negocio, ya
traducidas al modelo del sistema:

- **Un producto** = un alimento (por ejemplo, «Terneros Cuna»).
- **Una presentación** = un empaque concreto (por ejemplo, «saco 40 kg pellet»).
- **Unidad base**: el gramo (GR). El stock se acumula en gramos y cada
  empaque es un factor de conversión (un saco de 40 kg = 40 000 g).

Los precios de las listas son **lo que paga el negocio** (el costo). El precio
de venta se calcula con un margen sobre el costo, y ambos quedan guardados:
el costo como referencia y el precio de venta como el que se cobra.

Decisiones tomadas con el negocio:
- Margen del 30 % sobre el costo.
- Los productos VITAMAXPRO sin empaque en el nombre son sacos de 40 kg.
- Los códigos de VITAMAXPRO se inventan ordenados (VMP-001…); los dos
  productos de TOMASINO sin código usan TOM-SC-01 y TOM-SC-02.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

#: Margen sobre el costo para calcular el precio de venta.
MARGEN = Decimal("0.30")

#: Empaque por defecto de los productos VITAMAXPRO que no lo dicen en el nombre.
PESO_POR_DEFECTO_KG = 40


@dataclass(frozen=True)
class Empaque:
    """Una presentación: un formato y un peso, con su precio del distribuidor."""

    forma: str
    """PELLET, POLVO, HARINA…"""

    peso_kg: int
    """Peso del empaque en kilos."""

    precio_costo: str
    """Precio del empaque que paga el negocio."""

    bolsas: int | None = None
    """Cantidad de bolsas de 1 kg (si el empaque es «20 x 1 kg»)."""

    @property
    def nombre(self) -> str:
        """Nombre de la presentación, tal como se muestra en la interfaz."""
        if self.bolsas:
            return f"{self.peso_kg} x 1 kg {self.forma.lower()}"
        return f"saco {self.peso_kg} kg {self.forma.lower()}"

    @property
    def factor_base(self) -> int:
        """Cuántos gramos base tiene este empaque."""
        return self.peso_kg * 1000

    @property
    def costo_unitario_base(self) -> Decimal:
        """Costo por gramo (para el costo de referencia)."""
        return (
            Decimal(self.precio_costo) / Decimal(self.factor_base)
        ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Item:
    """Un producto del catálogo inicial."""

    proveedor: str
    categoria: str
    marca: str
    nombre: str
    codigo: str
    empaques: list[Empaque] = field(default_factory=list)
    nota: str = ""
    #: Si el producto se compra por un empaque concreto al proveedor.
    empaque_de_compra: str | None = None


def _precio_venta(costo: Decimal) -> Decimal:
    """Precio de venta a partir del costo y el margen."""
    return (costo * (Decimal("1") + MARGEN)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def precio_venta_de(costo: str | Decimal) -> str:
    """Precio de venta de un empaque, con el margen del 30 %."""
    return str(_precio_venta(Decimal(str(costo))))


# =============================================================================
# VITAMAXPRO / INVITA
# =============================================================================

#: (línea, nombre completo, precio pellet, precio polvo, nota)
_VITAMAXPRO: list[tuple[str, str, str, str, str]] = [
    ("Vacunos", "VITAMAXPRO TERNEROS CUNA", "88.00", "86.00", "Resaltado amarillo"),
    ("Vacunos", "VITAMAXPRO TERNEROS CRECIMIENTO", "83.00", "81.00", "Resaltado amarillo"),
    ("Vacunos", "VITAMAXPRO TERNEROS DESARROLLO", "77.50", "77.00", "Resaltado amarillo"),
    ("Vacunos", "VITAMAXPRO VACAS LECHERAS PRODUCCION 1600 -M", "70.50", "68.50", ""),
    ("Vacunos", "VITAMAXPRO VACAS LECHERAS PRODUCCION 1600", "72.50", "70.50", ""),
    ("Vacunos", "VITAMAXPRO VACAS LECHERAS ESPECIAL 1700", "77.50", "75.50", ""),
    ("Vacunos", "VITAMAXPRO VACAS LECHERAS ALTA 1800", "85.00", "83.00", ""),
    ("Vacunos", "VITAMAXPRO VACAS LECHERAS SUPER ALTA 1900", "89.00", "87.00", ""),
    ("Vacunos", "VITAMAXPRO VACAS PRE PARTO", "92.00", "91.50", ""),
    ("Vacunos", "VITAMAXPRO VACAS POST PARTO", "98.50", "96.50", ""),
    ("Vacunos", "VITAMAXPRO VACUNOS ENGORDE", "79.00", "78.00", ""),
    ("Vacunos", "VITAMAXPRO TOROS DE PELEA", "84.00", "83.50", ""),
    ("Ovinos", "VITAMAXPRO OVINOS CRECIMIENTO", "86.50", "-", ""),
    ("Ovinos", "VITAMAXPRO OVINOS EXPOSICION", "86.50", "-", ""),
    ("Cerdos", "VITAMAXPRO LECHON PLUS GOLD F-1 X 20 KG", "124.00", "-", ""),
    ("Cerdos", "VITAMAXPRO LECHON PLUS GOLD F-2 X40 KG", "174.00", "-", ""),
    ("Cerdos", "VITAMAXPRO CERDOS INICIO 1", "109.00", "107.00", ""),
    ("Cerdos", "VITAMAXPRO CERDOS INICIO 2", "100.00", "98.00", ""),
    ("Cerdos", "VITAMAXPRO CERDOS DESARROLLO 1", "90.00", "88.00", ""),
    ("Cerdos", "VITAMAXPRO CERDOS DESARROLLO 2", "88.00", "86.00", ""),
    ("Cerdos", "VITAMAXPRO CERDOS ENGORDE", "85.00", "83.00", ""),
    ("Cerdos", "VITAMAXPRO MARRANAS LACTANTES", "98.00", "96.00", ""),
    ("Cerdos", "VITAMAXPRO LEVANTE CHANCHILLAS", "87.00", "85.00", ""),
    ("Cerdos", "VITAMAXPRO MARRANA GESTANTES", "83.00", "81.00", ""),
    ("Cerdos", "VITAMAXPRO CERDOS DESARROLLO 1 X 50KG", "-", "110.00", ""),
    ("Cerdos", "VITAMAXPRO CERDOS DESARROLLO 2 X 50 KG", "-", "107.00", ""),
    ("Cerdos", "VITAMAXPRO CERDOS ENGORDE X 50 KG", "-", "101.00", ""),
    ("Cerdos", "VITAMAXPRO MARRANAS LACTANTES X 50 KG", "-", "116.00", ""),
    ("Cerdos", "VITAMAXPRO LEVANTE CHANCHILLAS X 50 KG", "-", "101.00", ""),
    ("Cerdos", "VITAMAXPRO MARRANA GESTANTE X 50 KG", "-", "99.00", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS INICIO PREMIUN X 40", "96.00", "94.00", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS CRECIMIENTO PREMIUN X 40", "93.00", "91.00", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS ENGORDE PREMIUN X 40", "92.00", "90.00", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS ENGORDE PREMIUN POLVO X 50", "-", "113.00", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS CRECIMIENTO PREMIUN X 20", "48.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS CRECIMIENTO PREMIUN POLVO X 50", "-", "114.00", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS ENGORDE PREMIUN X 20", "47.50", "-", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS INICIO PREMIUN 20X1 KG", "55.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS CRECIMIENTO PREMIUN 20X1 KG", "54.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS ENGORDE PREMIUN 20X1 KG", "54.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS ALTURA CRECIMIENTO X 40 KG", "90.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO POLLOS ALTURA ENGORDE X 40 KG", "88.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO PICO DE ORO INICIO X 20 KG", "64.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO PICO DE ORO CRECIMIENTO X 20 KG", "59.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO PICO DE ORO COMBATE X 20 KG", "54.50", "-", ""),
    ("Pollos granja", "VITAMAXPRO PICO DE ORO DESARROLLO X 20 KG", "54.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO PICO DE ORO INICIO 20x1 KG", "64.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO PICO DE ORO CRECIMIENTO 20x1 KG", "59.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO PICO DE ORO COMBATE 20x1 KG", "54.50", "-", ""),
    ("Pollos granja", "VITAMAXPRO AVEPROMICINA 20X1 KG", "60.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO AVEPROMICINA X 20", "60.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO AVEPROMICINA X 40", "118.00", "-", ""),
    ("Pollos granja", "VITAMAXPRO AVEPROMICINA X 40 MICROPELLET", "118.00", "-", ""),
    ("Postura", "VITAMAXPRO GALLINAS PRE-INICIO X 40", "106.00", "-", ""),
    ("Postura", "VITAMAXPRO GALLINAS INICIO X 40", "103.00", "-", ""),
    ("Postura", "VITAMAXPRO POSTURA CRECIMIENTO X 40", "95.00", "-", ""),
    ("Postura", "VITAMAXPRO PRE POSTURA X40", "95.00", "-", ""),
    ("Postura", "VITAMAXPRO POSTURA ESPECIAL 1 X 40", "94.50", "-", ""),
    ("Postura", "VITAMAXPRO GALLINA PONEDORAS X 40", "85.00", "83.00", ""),
    ("Pavos", "VITAMAXPRO PAVOS PRE INICIO", "123.00", "-", ""),
    ("Pavos", "VITAMAXPRO PAVOS INICIO", "104.50", "-", ""),
    ("Pavos", "VITAMAXPRO PAVOS CRECIMIENTO", "99.50", "-", ""),
    ("Pavos", "VITAMAXPRO PAVOS ENGORDE", "98.00", "-", ""),
    ("Patos", "VITAMAXPRO PATOS INICIO", "100.50", "-", ""),
    ("Patos", "VITAMAXPRO PATOS CRECIMIENTO", "91.50", "-", ""),
    ("Patos", "VITAMAXPRO PATOS ENGORDE", "90.00", "-", ""),
    ("Conejos y cuyes", "VITAMAXPRO CONEJOS CARNE", "81.00", "-", ""),
    ("Conejos y cuyes", "VITAMAXPRO CUYES CARNE", "86.50", "84.50", "Resaltado amarillo"),
    ("Conejos y cuyes", "VITAMAXPRO CUYES INICIO", "90.00", "-", "Resaltado amarillo"),
    ("Conejos y cuyes", "VITAMAXPRO CUYES CRECIMIENTO", "88.00", "-", "Resaltado amarillo"),
    (
        "Conejos y cuyes",
        "VITAMAXPRO CUYES CARNE POLVO PER-S X 40 KG",
        "87.00",
        "-",
        "Resaltado amarillo (Dice POLVO en el nombre, precio en la columna PELLET)",
    ),
    ("Conejos y cuyes", "VITAMAXPRO CUYES REPRODUCTORES", "91.00", "-", "Resaltado amarillo"),
    ("Caballos", "VITAMAXPRO CABALLOS COMPETENCIA", "82.00", "-", ""),
    ("Caballos", "VITAMAXPRO CABALLOS MANTENIMIENTO", "78.00", "-", ""),
    ("Invita", "INVITA AVES INICIO", "66.00", "-", ""),
    ("Invita", "INVITA AVES CRECIMIENTO", "65.00", "-", ""),
    ("Invita", "INVITA AVES ENGORDE", "64.50", "-", ""),
    ("Invita", "INVITA CERDOS INICIO", "94.00", "94.00", ""),
    ("Invita", "INVITA CERDOS CRECIMIENTO", "87.50", "97.50", ""),
    ("Invita", "INVITA CERDOS ENGORDE", "84.50", "84.50", ""),
    ("Invita", "INVITA MARRANAS LACTANTES", "92.50", "-", ""),
    ("Invita", "INVITA CUYES DOMESTICO", "81.50", "-", "Resaltado amarillo"),
    ("Invita", "INVITA POLLOS INICIO REFORZADO X 40", "77.00", "-", ""),
    ("Invita", "INVITA POLLOS CRECIMIENTO REFORZADO X 40", "75.50", "-", ""),
    ("Invita", "INVITA POLLOS ENGORDE REFORZADOX 40", "75.50", "-", ""),
    ("Invita", "INVITA POLLOS INICIO CASERITO X 40", "69.00", "-", ""),
    ("Invita", "INVITA POLLOS CRECIMIENTO CASERITO X 40", "68.00", "-", ""),
    ("Invita", "INVITA POLLOS ENGORDE CASERITO X 40", "68.00", "-", ""),
]

# =============================================================================
# TOMASINO
# =============================================================================

#: (código, presentación, peso kg, descripción, precio por saco, nota)
_TOMASINO: list[tuple[str, str, str, str, str, str]] = [
    ("11022", "PELLET", "20", "Broiler Tech Nutrition, 1x20", "84.00", ""),
    ("10897", "PELLET", "40", "Broiler Tech Nutrition, 1x40", "160.00", ""),
    ("11023", "PELLET", "20", "Layer Tech Nutrition, 1x20", "82.50", ""),
    ("10930", "PELLET", "40", "Layer Tech Nutrition, 1x40", "157.00", ""),
    ("7271", "PELLET", "20", "Avemed, 20 x 1", "64.00", ""),
    ("9990", "PELLET", "40", "Avemed, 1 x 40", "118.00", ""),
    ("5381", "PELLET", "40", "Pollos Inicio Tomasino, 1 x 40", "103.00", ""),
    ("5382", "PELLET", "40", "Pollos Crecimiento Tomasino, 1 x 40", "101.00", ""),
    ("5383", "PELLET", "40", "Pollos Acabado Tomasino, 1 x 40", "100.00", ""),
    ("11016", "HARINA", "40", "Concen Inicio Broiler, 1 x 40", "131.50", ""),
    ("11017", "HARINA", "40", "Concen Crecimiento Broiler, 1 x 40", "127.00", ""),
    ("11018", "HARINA", "40", "Concen Acabado Broiler, 1 x 40", "127.50", ""),
    ("5462", "PELLET", "20", "Pollos Inicio Tomasino Doméstico, 20 x 1", "52.00", ""),
    ("5463", "PELLET", "20", "Pollos Crecimiento Tomasino Doméstico, 20 x 1", "51.00", ""),
    ("5464", "PELLET", "20", "Pollos Acabado Tomasino Doméstico, 20 x 1", "50.00", ""),
    ("8863", "PELLET", "40", "Pollos Inicio Tomasino Doméstico EF, 1 x 40", "94.00", ""),
    ("8864", "PELLET", "40", "Pollos Crecimiento Tomasino Doméstico EF, 1 x 40", "91.00", ""),
    ("8865", "PELLET", "40", "Pollos Acabado Tomasino Doméstico EF, 1 x 40", "90.00", ""),
    ("5473", "PELLET", "40", "Inicio Postura Tomasino, 1 x 40", "105.00", ""),
    ("5474", "PELLET", "40", "Levante Postura Tomasino, 1 x 40", "99.00", ""),
    ("5475", "PELLET", "40", "Postura Tomasino, 1 x 40", "93.00", ""),
    ("5444", "PELLET", "40", "Pavos Pre Inicio Tomasino, 1 x 40", "135.00", ""),
    ("5445", "PELLET", "40", "Pavos Inicio Tomasino, 1 x 40", "111.00", ""),
    ("5446", "PELLET", "40", "Pavos Crecimiento Tomasino, 1 x 40", "106.00", ""),
    ("5447", "PELLET", "40", "Pavos Acabado Tomasino, 1 x 40", "103.00", ""),
    ("5477", "PELLET", "30", "Supervit Aves Inicio, 1 x 30", "55.00", ""),
    ("5478", "PELLET", "40", "Supervit Aves Crecimiento, 1 x 40", "72.00", ""),
    ("5479", "PELLET", "40", "Supervit Aves Acabado, 1 x 40", "72.00", ""),
    ("10935", "PELLET", "20", "Casta de Campeones Inicio, 20 x 1", "71.39", ""),
    ("10936", "PELLET", "20", "Casta de Campeones Crecimiento, 20 x 1", "62.60", ""),
    ("10937", "PELLET", "20", "Casta de Campeones Combate, 20 x 1", "60.40", ""),
    ("11008", "PELLET", "20", "Casta de Campeones Muda, 20 x 1", "63.00", "Disponible por temporada de muda."),
    ("10910", "PELLET", "40", "Casta de Campeones Inicio, 1 x 40", "127.83", ""),
    ("10911", "PELLET", "40", "Casta de Campeones Crecimiento, 1 x 40", "110.79", ""),
    ("10912", "PELLET", "40", "Casta de Campeones Combate, 1 x 40", "106.53", ""),
    ("10981", "PELLET", "40", "Casta de Campeones Muda, 1 x 40", "111.00", ""),
    ("10905", "PELLET", "40", "Pig Tech Nutrition 1, 1 x 40", "265.00", ""),
    ("10906", "PELLET", "40", "Pig Tech Nutrition 2, 1 x 40", "215.00", ""),
    ("10907", "PELLET", "40", "Pig Tech Nutrition 3, 1 x 40", "145.00", ""),
    ("5436", "PELLET", "40", "Cerdos Inicio Tomasino plus, 1 x 40", "115.00", ""),
    ("5437", "PELLET", "40", "Cerdos Desarrollo Tomasino, 1 x 40", "88.00", ""),
    ("11070", "HARINA", "50", "Supervit Cerdos Crecimiento 1 (harina) 1 X 50", "104.00", ""),
    ("11071", "HARINA", "50", "Supervit Cerdos Crecimiento 2 (harina) 1 X 50", "102.00", ""),
    ("11072", "HARINA", "50", "Supervit Cerdos Acabado (harina) 1 X 50", "101.40", ""),
    ("9712", "PELLET", "40", "Cerdos Crecimiento Tomasino I, 1 x 40", "93.00", ""),
    ("9713", "PELLET", "40", "Cerdos Crecimiento Tomasino II, 1 x 40", "91.00", ""),
    ("9714", "PELLET", "40", "Cerdos Acabado Tomasino, 1 x 40", "87.00", ""),
    ("9715", "PELLET", "40", "Cerdos Finalizador Tomasino, 1 x 40", "92.00", ""),
    ("5439", "PELLET", "40", "Marranas Lactantes Tomasino, 1 x 40", "98.00", ""),
    ("10441", "PELLET", "40", "Marranas Gestantes Tomasino, 1 x 40", "95.00", ""),
    ("11029", "PELLET", "40", "Calf Tech Nutrition", "137.00", ""),
    ("5379", "PELLET", "40", "Terneros Tomasino Plus, 1 x 40", "103.00", ""),
    ("9959", "PELLET", "40", "Vacas Pre Parto Tomasino, 1 x 40", "136.00", ""),
    ("11035", "PELLET", "40", "Terneras Crecimiento Tomasino, 1 x 40", "77.50", ""),
    ("11065", "PELLET", "40", "Vacas Secas Tomasino, 1 x 40", "76.00", ""),
    ("5429", "PELLET", "40", "Vacas Producción Tomasino Plus N°1, 1 x 40", "93.50", "Reemplazado por el 10540."),
    ("5432", "PELLET", "40", "Vacas Producción Tomasino N° 2, 1 x 40", "73.00", ""),
    ("10540", "PELLET", "40", "Vacas Super Alta Producción 2 Tomasino x 40", "93.50", ""),
    ("11050", "HARINA", "30", "Vacas Producción Tomasino Plus - Pastoreo x 30", "60.00", "Presentación a discontinuarse."),
    ("11093", "HARINA", "50", "Vacas Producción Tomasino Plus - Pastoreo x 50", "99.00", ""),
    ("5380", "PELLET", "40", "Toros Engorde Tomasino, 1 x 40", "79.50", ""),
    ("7252", "PELLET", "20", "Conejos Carne Tomasino, 20 x 1", "50.00", ""),
    ("11041", "PELLET", "40", "Conejina", "81.50", ""),
    ("S/C", "PELLET", "40", "Conejina R", "82.00", "Sin código en la lista del distribuidor."),
    ("11038", "PELLET", "40", "Cuyes Inicio Tomasino, 1 x 40", "86.00", ""),
    ("11039", "PELLET", "40", "Cuyes Crecimiento Tomasino, 1 x 40", "83.00", ""),
    ("11040", "PELLET", "40", "Cuyes Acabado Tomasino, 1 x 40", "81.50", ""),
    ("S/C", "PELLET", "40", "Cuyes Reproductores Tomasino", "82.50", "Sin código en la lista del distribuidor."),
    ("8692", "PELLET", "40", "Ovinos Tomasino, 1 x 40", "84.00", ""),
    ("11014", "PELLET", "40", "Equus Yegua y Potro", "111.00", ""),
    ("11012", "PELLET", "40", "Equus Adulto", "97.00", ""),
    ("11013", "PELLET", "40", "Equus Complete", "107.50", ""),
    ("5448", "PELLET", "40", "Caballos Tomasino, 1 x 40", "83.50", ""),
]

#: Categorías de TOMASINO, por código (las que no están, se deducen del nombre).
_CATEGORIAS_TOMASINO: dict[str, str] = {
    "11022": "Aves",
    "10897": "Aves",
    "11023": "Aves",
    "10930": "Aves",
    "7271": "Aves",
    "9990": "Aves",
    "5381": "Pollos granja",
    "5382": "Pollos granja",
    "5383": "Pollos granja",
    "11016": "Pollos granja",
    "11017": "Pollos granja",
    "11018": "Pollos granja",
    "5462": "Pollos granja",
    "5463": "Pollos granja",
    "5464": "Pollos granja",
    "8863": "Pollos granja",
    "8864": "Pollos granja",
    "8865": "Pollos granja",
    "5473": "Postura",
    "5474": "Postura",
    "5475": "Postura",
    "5444": "Pavos",
    "5445": "Pavos",
    "5446": "Pavos",
    "5447": "Pavos",
    "5477": "Aves",
    "5478": "Aves",
    "5479": "Aves",
    "10935": "Gallos de pelea",
    "10936": "Gallos de pelea",
    "10937": "Gallos de pelea",
    "11008": "Gallos de pelea",
    "10910": "Gallos de pelea",
    "10911": "Gallos de pelea",
    "10912": "Gallos de pelea",
    "10981": "Gallos de pelea",
    "10905": "Cerdos",
    "10906": "Cerdos",
    "10907": "Cerdos",
    "5436": "Cerdos",
    "5437": "Cerdos",
    "11070": "Cerdos",
    "11071": "Cerdos",
    "11072": "Cerdos",
    "9712": "Cerdos",
    "9713": "Cerdos",
    "9714": "Cerdos",
    "9715": "Cerdos",
    "5439": "Cerdos",
    "10441": "Cerdos",
    "11029": "Vacunos",
    "5379": "Vacunos",
    "9959": "Vacunos",
    "11035": "Vacunos",
    "11065": "Vacunos",
    "5429": "Vacunos",
    "5432": "Vacunos",
    "10540": "Vacunos",
    "11050": "Vacunos",
    "11093": "Vacunos",
    "5380": "Vacunos",
    "7252": "Conejos y cuyes",
    "11041": "Conejos y cuyes",
    "11038": "Conejos y cuyes",
    "11039": "Conejos y cuyes",
    "11040": "Conejos y cuyes",
    "8692": "Ovinos",
    "11014": "Caballos",
    "11012": "Caballos",
    "11013": "Caballos",
    "5448": "Caballos",
}
