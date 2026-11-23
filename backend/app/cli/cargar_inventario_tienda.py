"""Carga el inventario físico de la tienda (`inventario_tienda.md` / `inventario tienda.xlsx`).

Ejecuta en orden:
1. Fusión y desactivación de duplicados del catálogo base (Tomasino por empaque
   y cruces de marca Invita/Vitamaxpro).
2. Alta o actualización de los productos y presentaciones de las 7 secciones
   del archivo de inventario de la tienda (Vitamax, Tomasino, Sequeiros,
   Perro y gatos, Producto primario, Medicamento y Bolsas).
3. Aplicación de la regla «1/2 saco»:
   - `si` -> `permite_fraccion = True` (habilita venta de 1/2 saco = -0.5 saco).
   - `no` -> `permite_fraccion = False` (solo venta por sacos enteros).
4. Registro del stock del conteo físico como lotes de `INVENTARIO_INICIAL`,
   tomando el `costo_referencia` del catálogo cuando existe (y `0` en los
   productos nuevos cuyo costo se registrará al recibir mercadería).

Uso:
    python -m app.cli.cargar_inventario_tienda --simular
    python -m app.cli.cargar_inventario_tienda
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


def _preparar_consola() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


_preparar_consola()

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Almacen,
    Categoria,
    Existencia,
    LoteInventario,
    Marca,
    PresentacionProducto,
    Producto,
    ProductoProveedor,
    Proveedor,
    TipoMovimiento,
    UnidadMedida,
    Usuario,
)
from app.db.session import SessionLocal
from app.domain.unidades import dec, q2, q4, q6
from app.services import catalogo, existencias, inventario
from app.services import lotes as servicio_lotes

#: Pares (codigo_conservar, codigo_desactivar) a fusionar en un solo producto.
FUSIONES_DUPLICADOS: list[tuple[str, str]] = [
    ("7271", "9990"),  # Avemed (20x1 kg + saco 40 kg)
    ("10897", "11022"),  # Broiler Tech Nutrition (40 kg + 20 kg)
    ("10930", "11023"),  # Layer Tech Nutrition (40 kg + 20 kg)
    ("10910", "10935"),  # Casta de Campeones Inicio (40 kg + 20x1 kg)
    ("10911", "10936"),  # Casta de Campeones Crecimiento (40 kg + 20x1 kg)
    ("10912", "10937"),  # Casta de Campeones Combate (40 kg + 20x1 kg)
    ("10981", "11008"),  # Casta de Campeones Muda (40 kg + 20x1 kg)
    ("INV-005", "VMP-006"),  # CERDOS ENGORDE (conserva Invita)
    ("INV-008", "VMP-023"),  # MARRANAS LACTANTES (conserva Invita)
]


@dataclass(frozen=True)
class ItemConteo:
    """Una línea del inventario físico de la tienda."""

    codigo: str
    nombre: str
    categoria: str
    marca: str
    unidad_base: str  # GR | ML | UND
    presentacion: str
    factor_base: str
    cantidad: str  # en unidades de la presentación (sacos, bolsas, goteros...)
    medio_saco: bool
    proveedor: str | None = None


#: Las 127 líneas de `inventario_tienda.md` mapeadas al catálogo.
ITEMS_INVENTARIO_TIENDA: list[ItemConteo] = [
    # --- 1. producto vitamax (26 líneas) ------------------------------------
    ItemConteo("INV-001", "AVES CRECIMIENTO", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "137", True, "Vitamaxpro"),
    ItemConteo("VMP-039", "POLLOS CRECIMIENTO PREMIUN", "Pollos granja", "Vitamaxpro", "GR", "saco 20 kg pellet", "20000", "6", False, "Vitamaxpro"),
    ItemConteo("INV-002", "AVES ENGORDE", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "116", True, "Vitamaxpro"),
    ItemConteo("VMP-040", "POLLOS ENGORDE PREMIUN", "Pollos granja", "Vitamaxpro", "GR", "saco 20 kg pellet", "20000", "4", False, "Vitamaxpro"),
    ItemConteo("INV-003", "AVES INICIO", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "93", False, "Vitamaxpro"),
    ItemConteo("VMP-001", "AVEPROMICINA", "Pollos granja", "Vitamaxpro", "GR", "saco 20 kg pellet", "20000", "14", False, "Vitamaxpro"),
    ItemConteo("VMP-001", "AVEPROMICINA", "Pollos granja", "Vitamaxpro", "GR", "saco 40 kg pellet", "40000", "7", False, "Vitamaxpro"),
    ItemConteo("VMP-057", "PESCADO INICIO", "Peces", "Vitamaxpro", "GR", "saco 40 kg", "40000", "0", False, "Vitamaxpro"),
    ItemConteo("VMP-058", "AGUA PRO PESCADO CRECIMIENTO 1", "Peces", "Vitamaxpro", "GR", "saco 40 kg", "40000", "65", False, "Vitamaxpro"),
    ItemConteo("VMP-059", "AGUA PRO PESCADO CRECIMIENTO 2", "Peces", "Vitamaxpro", "GR", "saco 40 kg", "40000", "57", False, "Vitamaxpro"),
    ItemConteo("VMP-060", "AGUA PRO PESCADO ACABADO 1", "Peces", "Vitamaxpro", "GR", "saco 40 kg", "40000", "30", False, "Vitamaxpro"),
    ItemConteo("VMP-061", "AGUA PRO PESCADO ACABADO 2", "Peces", "Vitamaxpro", "GR", "saco 40 kg", "40000", "0", False, "Vitamaxpro"),
    ItemConteo("VMP-014", "CUYES REPRODUCTORES", "Conejos y cuyes", "Vitamaxpro", "GR", "saco 40 kg pellet", "40000", "49", False, "Vitamaxpro"),
    ItemConteo("INV-009", "POLLOS CRECIMIENTO CASERITO", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "30", False, "Vitamaxpro"),
    ItemConteo("INV-011", "POLLOS ENGORDE CASERITO", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "11", False, "Vitamaxpro"),
    ItemConteo("INV-010", "POLLOS CRECIMIENTO REFORZADO", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "19", False, "Vitamaxpro"),
    ItemConteo("INV-012", "POLLOS ENGORDE REFORZADO", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "13", False, "Vitamaxpro"),
    ItemConteo("VMP-015", "GALLINA PONEDORAS", "Postura", "Vitamaxpro", "GR", "saco 40 kg pellet", "40000", "20", False, "Vitamaxpro"),
    ItemConteo("INV-007", "CUYES DOMESTICO", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "48", False, "Vitamaxpro"),
    ItemConteo("VMP-056", "VACUNOS ENGORDE", "Vacunos", "Vitamaxpro", "GR", "saco 40 kg pellet", "40000", "7", False, "Vitamaxpro"),
    ItemConteo("VMP-062", "TRUCHA INICIO 25 KG", "Peces", "Vitamaxpro", "GR", "saco 25 kg", "25000", "2", False, "Vitamaxpro"),
    ItemConteo("VMP-063", "TRUCHA ACABADO 25 KG", "Peces", "Vitamaxpro", "GR", "saco 25 kg", "25000", "5", False, "Vitamaxpro"),
    ItemConteo("VMP-005", "CERDOS DESARROLLO 2", "Cerdos", "Vitamaxpro", "GR", "saco 40 kg pellet", "40000", "40", False, "Vitamaxpro"),
    ItemConteo("INV-005", "CERDOS ENGORDE", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "23", False, "Vitamaxpro"),
    ItemConteo("VMP-064", "TRUCHA CRECIMIENTO 2 X 25 KG", "Peces", "Vitamaxpro", "GR", "saco 25 kg", "25000", "2", False, "Vitamaxpro"),
    ItemConteo("INV-008", "MARRANAS LACTANTES", "Invita", "Invita", "GR", "saco 40 kg pellet", "40000", "4", False, "Vitamaxpro"),

    # --- 2. producto tomasino (10 líneas) -----------------------------------
    ItemConteo("7271", "Avemed", "Aves", "Tomasino", "GR", "20 x 1 kg pellet", "20000", "136", False, "Tomasino"),
    ItemConteo("11039", "Cuyes Crecimiento Tomasino", "Conejos y cuyes", "Tomasino", "GR", "saco 40 kg pellet", "40000", "17", False, "Tomasino"),
    ItemConteo("5382", "Pollos Crecimiento Tomasino", "Pollos granja", "Tomasino", "GR", "saco 40 kg pellet", "40000", "5", False, "Tomasino"),
    ItemConteo("5463", "Pollos Crecimiento Tomasino Doméstico", "Pollos granja", "Tomasino", "GR", "20 x 1 kg pellet", "20000", "1", False, "Tomasino"),
    ItemConteo("11041", "Conejina", "Conejos y cuyes", "Tomasino", "GR", "saco 40 kg pellet", "40000", "40", False, "Tomasino"),
    ItemConteo("7271", "Avemed", "Aves", "Tomasino", "GR", "saco 40 kg pellet", "40000", "9", False, "Tomasino"),
    ItemConteo("11071", "Supervit Cerdos Crecimiento 2 (harina)", "Cerdos", "Tomasino", "GR", "saco 50 kg harina", "50000", "115", False, "Tomasino"),
    ItemConteo("TOM-PES-01", "Inicio Pescado Tomasino 40 kg", "Peces", "Tomasino", "GR", "saco 40 kg", "40000", "17", False, "Tomasino"),
    ItemConteo("TOM-PES-02", "Crecimiento 1 Pescado Tomasino 40 kg", "Peces", "Tomasino", "GR", "saco 40 kg", "40000", "131", False, "Tomasino"),
    ItemConteo("TOM-PES-03", "Crecimiento 2 Pescado Tomasino 40 kg", "Peces", "Tomasino", "GR", "saco 40 kg", "40000", "0", False, "Tomasino"),

    # --- 3. producto sequeiros (8 líneas) -----------------------------------
    ItemConteo("SEQ-001", "Concentrado Crecimiento Polvo", "Sequeiros", "Sequeiros", "GR", "saco 40 kg polvo", "40000", "11", True),
    ItemConteo("SEQ-002", "Concentrado Acabado Polvo", "Sequeiros", "Sequeiros", "GR", "saco 40 kg polvo", "40000", "0", True),
    ItemConteo("SEQ-003", "Concentrado Inicio Polvo", "Sequeiros", "Sequeiros", "GR", "saco 40 kg polvo", "40000", "0", True),
    ItemConteo("SEQ-004", "Cerdo Crecimiento Sequeiros", "Sequeiros", "Sequeiros", "GR", "saco 40 kg", "40000", "0", True),
    ItemConteo("SEQ-005", "Cerdo Acabado Sequeiros", "Sequeiros", "Sequeiros", "GR", "saco 40 kg", "40000", "0", True),
    ItemConteo("SEQ-006", "Cerdo Inicio Sequeiros", "Sequeiros", "Sequeiros", "GR", "saco 40 kg", "40000", "0", False),
    ItemConteo("SEQ-007", "Cuy Polvo Sequeiros", "Sequeiros", "Sequeiros", "GR", "saco 40 kg polvo", "40000", "10", True),
    ItemConteo("SEQ-008", "Concentrado Rancio Sequeiros", "Sequeiros", "Sequeiros", "GR", "saco 40 kg", "40000", "11", False),

    # --- 4. producto perro y gatos (17 líneas) ------------------------------
    ItemConteo("MAS-001", "Thor Azul 25 kg", "Perro y gatos", "Thor", "GR", "saco 25 kg", "25000", "10", False),
    ItemConteo("MAS-002", "Super Can", "Perro y gatos", "Super Can", "GR", "saco 25 kg", "25000", "0", False),
    ItemConteo("MAS-003", "Bosko Verde 15 kg", "Perro y gatos", "Bosko", "GR", "saco 15 kg", "15000", "9", False),
    ItemConteo("MAS-004", "Bosko Rojo 15 kg", "Perro y gatos", "Bosko", "GR", "saco 15 kg", "15000", "34", False),
    ItemConteo("MAS-005", "Zeus", "Perro y gatos", "Zeus", "GR", "saco 15 kg", "15000", "0", False),
    ItemConteo("MAS-006", "Ricocan Adulto 18 kg", "Perro y gatos", "Ricocan", "GR", "saco 18 kg", "18000", "22", False),
    ItemConteo("MAS-007", "Ricocan Cachorro 15 kg", "Perro y gatos", "Ricocan", "GR", "saco 15 kg", "15000", "18", False),
    ItemConteo("MAS-008", "Ricocan Cachorro 1 kg", "Perro y gatos", "Ricocan", "GR", "bolsa 1 kg", "1000", "6", False),
    ItemConteo("MAS-009", "Michicat 18 kg", "Perro y gatos", "Michicat", "GR", "saco 18 kg", "18000", "9", False),
    ItemConteo("MAS-010", "Michicat 9 kg", "Perro y gatos", "Michicat", "GR", "saco 9 kg", "9000", "8", False),
    ItemConteo("MAS-011", "Ktito 15 kg", "Perro y gatos", "Ktito", "GR", "saco 15 kg", "15000", "9", False),
    ItemConteo("MAS-012", "Supercat Morado 9 kg", "Perro y gatos", "Supercat", "GR", "saco 9 kg", "9000", "7", False),
    ItemConteo("MAS-013", "Ricocat Cachorro 1 kg", "Perro y gatos", "Ricocat", "GR", "bolsa 1 kg", "1000", "10", False),
    ItemConteo("MAS-014", "Ricocat Adulto Salmón Atún Carne y Pollo 9 kg (Morado)", "Perro y gatos", "Ricocat", "GR", "saco 9 kg", "9000", "11", False),
    ItemConteo("MAS-015", "Ricocat Cachorro Carne Pescado y Leche 9 kg (Rosado)", "Perro y gatos", "Ricocat", "GR", "saco 9 kg", "9000", "16", False),
    ItemConteo("MAS-016", "Mimascot Adulto Carne 24 kg", "Perro y gatos", "Mimascot", "GR", "saco 24 kg", "24000", "1", False),
    ItemConteo("MAS-017", "Mimascot Adulto Mix Sabores 24 kg", "Perro y gatos", "Mimascot", "GR", "saco 24 kg", "24000", "1", False),

    # --- 5. producto primario (18 líneas) -----------------------------------
    ItemConteo("PRI-001", "Maíz Completo", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "81", True),
    ItemConteo("PRI-002", "Maíz Quintal", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "34", True),
    ItemConteo("PRI-003", "Maíz x 20 kg", "Producto primario", "Primario", "GR", "saco 20 kg", "20000", "5", True),
    ItemConteo("PRI-004", "Maíz Quintal con Polvo II", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "5", True),
    ItemConteo("PRI-005", "Maíz Quintal con Polvo III", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "10", True),
    ItemConteo("PRI-006", "Maíz Chancado Mediano 38 kg", "Producto primario", "Primario", "GR", "saco 38 kg", "38000", "39", True),
    ItemConteo("PRI-007", "Maíz Chancado Mediano x 20 kg", "Producto primario", "Primario", "GR", "saco 20 kg", "20000", "0", True),
    ItemConteo("PRI-008", "Maíz Chancado Granulado 38 kg", "Producto primario", "Primario", "GR", "saco 38 kg", "38000", "86", True),
    ItemConteo("PRI-009", "Maíz Chancado Granulado x 20 kg", "Producto primario", "Primario", "GR", "saco 20 kg", "20000", "5", True),
    ItemConteo("PRI-010", "Maíz Chancado Inicio 38 kg", "Producto primario", "Primario", "GR", "saco 38 kg", "38000", "11", True),
    ItemConteo("PRI-011", "Maíz Chancado Inicio x 20 kg", "Producto primario", "Primario", "GR", "saco 20 kg", "20000", "0", True),
    ItemConteo("PRI-012", "Sal 1 x 20 kg", "Producto primario", "Primario", "GR", "saco 20 kg", "20000", "40", False),
    ItemConteo("PRI-013", "Arrocillo 50 kg", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "32", True),
    ItemConteo("PRI-014", "Afrecho de Trigo 40 kg", "Producto primario", "Primario", "GR", "saco 40 kg", "40000", "41", True),
    ItemConteo("PRI-015", "Afrecho Don Máximo 40 kg", "Producto primario", "Primario", "GR", "saco 40 kg", "40000", "75", True),
    ItemConteo("PRI-016", "Torta de Soya", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "49", True),
    ItemConteo("PRI-017", "Alfalfa", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "6", True),
    ItemConteo("PRI-018", "Cascarilla de Arroz", "Producto primario", "Primario", "GR", "saco 50 kg", "50000", "5", False),

    # --- 6. medicamento (45 líneas) -----------------------------------------
    ItemConteo("MED-001", "Vetex - Broncoaviar Polvo 1 kg", "Medicamentos", "Vetex", "UND", "bolsa 1 kg", "1", "5", False),
    ItemConteo("MED-002", "Vetex - Nutramil Polvo (Complejo B) 1 kg", "Medicamentos", "Vetex", "UND", "bolsa 1 kg", "1", "8", False),
    ItemConteo("MED-003", "Vetex - Sulfabro 1 kg", "Medicamentos", "Vetex", "UND", "bolsa 1 kg", "1", "5", False),
    ItemConteo("MED-004", "Curabichera 500 ml (Spray)", "Medicamentos", "Veterinaria", "UND", "lata spray 500 ml", "1", "6", False),
    ItemConteo("MED-005", "Matabichera 500 ml (Spray)", "Medicamentos", "Veterinaria", "UND", "lata spray 500 ml", "1", "12", False),
    ItemConteo("MED-006", "Clorafen 20 gr", "Medicamentos", "Veterinaria", "UND", "bolsa 20 gr", "1", "102", False),
    ItemConteo("MED-007", "Dermil Perros 15 gr", "Medicamentos", "Veterinaria", "UND", "crema 15 gr", "1", "2", False),
    ItemConteo("MED-008", "Sensapet 120.5 gr", "Medicamentos", "Veterinaria", "UND", "crema 120.5 gr", "1", "1", False),
    ItemConteo("MED-009", "Pulgón Plus 25 gr", "Medicamentos", "Veterinaria", "UND", "sobre 25 gr", "1", "2", False),
    ItemConteo("MED-010", "Vetex - Broncoaviar Solución Oral (Gotas) 30 ml", "Medicamentos", "Vetex", "UND", "gotero 30 ml", "1", "52", False),
    ItemConteo("MED-011", "Triomicin R Solución Oral (Gotas) 30 ml", "Medicamentos", "Veterinaria", "UND", "gotero 30 ml", "1", "13", False),
    ItemConteo("MED-012", "Finox 30 ml", "Medicamentos", "Veterinaria", "UND", "gotero 30 ml", "1", "14", False),
    ItemConteo("MED-013", "Endotrex Gel Oral 5 ml", "Medicamentos", "Veterinaria", "UND", "gel 5 ml", "1", "3", False),
    ItemConteo("MED-014", "Endotrex Gel Oral 10 ml", "Medicamentos", "Veterinaria", "UND", "gel 10 ml", "1", "5", False),
    ItemConteo("MED-015", "Parasitox - Cuy NF 15 ml", "Medicamentos", "Veterinaria", "UND", "gotero 15 ml", "1", "4", False),
    ItemConteo("MED-016", "Tilox NF 15 ml", "Medicamentos", "Veterinaria", "UND", "gotero 15 ml", "1", "3", False),
    ItemConteo("MED-017", "Vetex - Ectofin 30 ml", "Medicamentos", "Vetex", "UND", "gotero 30 ml", "1", "12", False),
    ItemConteo("MED-018", "Vetex - Ectofin 25 ml", "Medicamentos", "Vetex", "UND", "botella 25 ml", "1", "44", False),
    ItemConteo("MED-019", "Vetex - Nutramil Oral 100 ml", "Medicamentos", "Vetex", "UND", "gotero 100 ml", "1", "37", False),
    ItemConteo("MED-020", "Vetex - Vetrazuril K 120 ml", "Medicamentos", "Vetex", "UND", "botella 120 ml", "1", "20", False),
    ItemConteo("MED-021", "Tableta Plan Dog 10 unidades x tb", "Medicamentos", "Veterinaria", "UND", "blister 10 tabletas", "1", "2", False),
    ItemConteo("MED-022", "Tilox Polvo 100 gr", "Medicamentos", "Veterinaria", "UND", "bolsa 100 gr", "1", "5", False),
    ItemConteo("MED-023", "Shampoo Ricocan 40 ml", "Medicamentos", "Ricocan", "UND", "sachet 40 ml", "1", "6", False),
    ItemConteo("MED-024", "Vetex - Vetrazuril K 1000 ml", "Medicamentos", "Vetex", "UND", "botella 1000 ml", "1", "3", False),
    ItemConteo("MED-025", "Vetex - Oxipro L.A 100 ml", "Medicamentos", "Vetex", "UND", "frasco 100 ml", "1", "2", False),
    ItemConteo("MED-026", "Ebredol Max 50 ml (Spray)", "Medicamentos", "Veterinaria", "UND", "spray 50 ml", "1", "1", False),
    ItemConteo("MED-027", "Tilox Inyectable 20 ml", "Medicamentos", "Veterinaria", "UND", "botella 20 ml", "1", "3", False),
    ItemConteo("MED-028", "Tilox Inyectable 10 ml", "Medicamentos", "Veterinaria", "UND", "botella 10 ml", "1", "3", False),
    ItemConteo("MED-029", "Vetex - Fenex 4% 10 gr", "Medicamentos", "Vetex", "UND", "sobre 10 gr", "1", "50", False),
    ItemConteo("MED-030", "Vetex - Sulfabro 10 gr", "Medicamentos", "Vetex", "UND", "sobre 10 gr", "1", "63", False),
    ItemConteo("MED-031", "Vetex - Vitaciclina 10 gr", "Medicamentos", "Vetex", "UND", "sobre 10 gr", "1", "90", False),
    ItemConteo("MED-032", "Vetex - Nutramil 10 gr", "Medicamentos", "Vetex", "UND", "sobre 10 gr", "1", "31", False),
    ItemConteo("MED-033", "Vetex - Nutramil (Complejo B) 10 gr", "Medicamentos", "Vetex", "UND", "sobre 10 gr", "1", "68", False),
    ItemConteo("MED-034", "Vetex - Broncoaviar 10 gr", "Medicamentos", "Vetex", "UND", "sobre 10 gr", "1", "229", False),
    ItemConteo("MED-035", "Keep Mata Pulgas y Garrapatas (Spray)", "Medicamentos", "Veterinaria", "UND", "lata spray", "1", "4", False),
    ItemConteo("MED-036", "Vetex - Fenex 4% 100 gr", "Medicamentos", "Vetex", "UND", "sobre 100 gr", "1", "9", False),
    ItemConteo("MED-037", "Vetex - Nutramil (Complejo B) 100 gr", "Medicamentos", "Vetex", "UND", "sobre 100 gr", "1", "61", False),
    ItemConteo("MED-038", "Vetex - Sulfabro 100 gr", "Medicamentos", "Vetex", "UND", "sobre 100 gr", "1", "3", False),
    ItemConteo("MED-039", "Vetex - Broncoaviar 100 gr", "Medicamentos", "Vetex", "UND", "sobre 100 gr", "1", "39", False),
    ItemConteo("MED-040", "Vetex - Vitaciclina 100 gr", "Medicamentos", "Vetex", "UND", "sobre 100 gr", "1", "8", False),
    ItemConteo("MED-041", "Clorafen 100 gr", "Medicamentos", "Veterinaria", "UND", "sobre 100 gr", "1", "2", False),
    ItemConteo("MED-042", "Plumas Polvo 100 gr", "Medicamentos", "Veterinaria", "UND", "sobre 100 gr", "1", "1", False),
    ItemConteo("MED-043", "Febenkur B12 100 gr", "Medicamentos", "Veterinaria", "UND", "sobre 100 gr", "1", "1", False),
    ItemConteo("MED-044", "Terramicin 100 gr", "Medicamentos", "Veterinaria", "UND", "sobre 100 gr", "1", "4", False),
    ItemConteo("MED-045", "Romy - Complejo B 10 gr", "Medicamentos", "Romy", "UND", "sobre 10 gr", "1", "50", False),

    # --- 7. bolsas (4 líneas) -----------------------------------------------
    ItemConteo("BOL-001", "Bolsa de 12x17 - Fabripack", "Bolsas", "Fabripack", "UND", "paquete", "1", "67", False),
    ItemConteo("BOL-002", "Bolsa de 8x12 - Fabripack", "Bolsas", "Fabripack", "UND", "paquete", "1", "38", False),
    ItemConteo("BOL-003", "Bolsa de 10x15 - Fabripack", "Bolsas", "Fabripack", "UND", "paquete", "1", "20", False),
    ItemConteo("BOL-004", "Bolsa de 10x15 - Pingüino", "Bolsas", "Pingüino", "UND", "paquete", "1", "6", False),
]


def _obtener_crear_categoria(db: Session, nombre: str) -> Categoria:
    cat = db.execute(
        select(Categoria).where(func.lower(Categoria.nombre) == nombre.strip().lower())
    ).scalar_one_or_none()
    if cat is None:
        cat = Categoria(nombre=nombre.strip(), activo=True)
        db.add(cat)
        db.flush()
    return cat


def _obtener_crear_marca(db: Session, nombre: str) -> Marca:
    marca = db.execute(
        select(Marca).where(func.lower(Marca.nombre) == nombre.strip().lower())
    ).scalar_one_or_none()
    if marca is None:
        marca = Marca(nombre=nombre.strip(), activo=True)
        db.add(marca)
        db.flush()
    return marca


def fusionar_duplicados(db: Session) -> int:
    """Fusiona las presentaciones en el producto principal y desactiva el duplicado."""
    fusionados = 0
    for codigo_principal, codigo_secundario in FUSIONES_DUPLICADOS:
        principal = db.execute(
            select(Producto).where(func.lower(Producto.codigo) == codigo_principal.lower())
        ).scalar_one_or_none()
        secundario = db.execute(
            select(Producto).where(func.lower(Producto.codigo) == codigo_secundario.lower())
        ).scalar_one_or_none()
        if principal is None or secundario is None:
            continue

        nombres_en_principal = {p.nombre.lower(): p for p in principal.presentaciones}
        for pres in list(secundario.presentaciones):
            existente = nombres_en_principal.get(pres.nombre.lower())
            if existente is None:
                nueva = PresentacionProducto(
                    producto_id=principal.id,
                    nombre=pres.nombre,
                    factor_base=pres.factor_base,
                    precio_venta=pres.precio_venta,
                    costo_referencia=pres.costo_referencia,
                    codigo_barras=pres.codigo_barras,
                    es_compra=pres.es_compra,
                    es_venta=pres.es_venta,
                    permite_fraccion=pres.permite_fraccion,
                    activo=True,
                )
                db.add(nueva)
                db.flush()
                nombres_en_principal[pres.nombre.lower()] = nueva
            pres.activo = False

        if secundario.activo:
            secundario.activo = False
            fusionados += 1

    db.flush()
    return fusionados


def cargar_inventario_tienda(db: Session, simular: bool = False) -> dict[str, int]:
    """Ejecuta la fusión, sincroniza los 127 ítems y carga el inventario inicial."""
    if simular:
        con_stock = sum(1 for item in ITEMS_INVENTARIO_TIENDA if dec(item.cantidad) > 0)
        sin_stock = len(ITEMS_INVENTARIO_TIENDA) - con_stock
        return {
            "lineas_lista": len(ITEMS_INVENTARIO_TIENDA),
            "fusiones": len(FUSIONES_DUPLICADOS),
            "productos_nuevos": 0,
            "productos_actualizados": 0,
            "lotes_iniciales": con_stock,
            "lineas_sin_stock": sin_stock,
        }

    unidades = {
        u.codigo: u
        for u in db.execute(select(UnidadMedida)).scalars().all()
    }
    for cod in ("GR", "ML", "UND"):
        if cod not in unidades:
            raise RuntimeError(f"Falta la unidad {cod}. Ejecute primero el instalador.")

    almacen = db.execute(
        select(Almacen).where(Almacen.activo.is_(True)).order_by(Almacen.id)
    ).scalars().first()
    if almacen is None:
        raise RuntimeError("No hay un almacén activo configurado.")

    admin = db.execute(select(Usuario).order_by(Usuario.id)).scalars().first()
    usuario_id = admin.id if admin else None

    proveedores = {
        p.razon_social.lower(): p
        for p in db.execute(select(Proveedor)).scalars().all()
    }

    fusiones = fusionar_duplicados(db)
    nuevos = 0
    actualizados = 0
    lotes_creados = 0
    sin_stock = 0

    #: Los ítems se agrupan por producto: la regla «1/2 saco» es del producto
    #: completo (el permiso de fracción del producto manda sobre el de la
    #: presentación), así que se aplica a todas sus presentaciones.
    por_producto: dict[str, list[ItemConteo]] = {}
    for item in ITEMS_INVENTARIO_TIENDA:
        por_producto.setdefault(item.codigo, []).append(item)

    for codigo, items in por_producto.items():
        reglas = {item.medio_saco for item in items}
        if len(reglas) > 1:
            raise RuntimeError(
                f"El producto {codigo} tiene reglas de «1/2 saco» contradictorias: {reglas}"
            )
        medio_saco = reglas.pop()
        item = items[0]

        categoria = _obtener_crear_categoria(db, item.categoria)
        marca = _obtener_crear_marca(db, item.marca)
        unidad = unidades[item.unidad_base]

        producto = db.execute(
            select(Producto).where(func.lower(Producto.codigo) == codigo.lower())
        ).scalar_one_or_none()

        if producto is None:
            producto = catalogo.crear_producto(
                db,
                {
                    "codigo": item.codigo,
                    "nombre": item.nombre,
                    "descripcion": None,
                    "categoria_id": categoria.id,
                    "marca_id": marca.id,
                    "unidad_base_id": unidad.id,
                    "stock_minimo_base": "0",
                    "permite_fraccion": medio_saco,
                    "activo": True,
                    "presentaciones": [
                        {
                            "nombre": items[0].presentacion,
                            "factor_base": items[0].factor_base,
                            "precio_venta": "0",
                            "costo_referencia": "0",
                            "codigo_barras": None,
                            "es_compra": True,
                            "es_venta": True,
                            "permite_fraccion": medio_saco,
                        }
                    ],
                },
            )
            nuevos += 1
        else:
            producto.activo = True
            producto.nombre = item.nombre
            producto.nombre_normalizado = catalogo.normalizar(item.nombre)
            producto.categoria_id = categoria.id
            producto.marca_id = marca.id
            producto.unidad_base_id = unidad.id
            actualizados += 1

        # --- Presentaciones de este producto --------------------------------
        presentaciones: dict[str, PresentacionProducto] = {}
        for item_linea in items:
            existente = next(
                (
                    p
                    for p in producto.presentaciones
                    if p.nombre.lower() == item_linea.presentacion.lower()
                ),
                None,
            )
            if existente is None:
                existente = PresentacionProducto(
                    producto_id=producto.id,
                    nombre=item_linea.presentacion,
                    factor_base=dec(item_linea.factor_base),
                    precio_venta=Decimal("0"),
                    costo_referencia=Decimal("0"),
                    codigo_barras=None,
                    es_compra=True,
                    es_venta=True,
                    permite_fraccion=medio_saco,
                    activo=True,
                )
                db.add(existente)
                db.flush()
            else:
                existente.activo = True
            presentaciones[existente.nombre.lower()] = existente

        # La regla «1/2 saco» se aplica al producto y a todas sus
        # presentaciones activas: si dice «no», solo se vende por sacos enteros.
        producto.permite_fraccion = medio_saco
        for presentacion in producto.presentaciones:
            if presentacion.activo:
                presentacion.permite_fraccion = medio_saco
        db.flush()

        for item_linea in items:
            presentacion = presentaciones[item_linea.presentacion.lower()]

            if item_linea.proveedor:
                prv = proveedores.get(item_linea.proveedor.lower())
                if prv is not None:
                    vinculo = db.execute(
                        select(ProductoProveedor).where(
                            ProductoProveedor.producto_id == producto.id,
                            ProductoProveedor.proveedor_id == prv.id,
                        )
                    ).scalar_one_or_none()
                    if vinculo is None:
                        db.add(
                            ProductoProveedor(
                                producto_id=producto.id,
                                proveedor_id=prv.id,
                                habitual=True,
                                presentacion_id=presentacion.id,
                            )
                        )
                        db.flush()

            cantidad_pres = dec(item_linea.cantidad)
            if cantidad_pres <= 0:
                sin_stock += 1
                continue

            factor = dec(presentacion.factor_base)
            cantidad_base = q4(cantidad_pres * factor)
            costo_ref = dec(presentacion.costo_referencia or 0)
            costo_base = q6(costo_ref / factor) if factor > 0 and costo_ref > 0 else Decimal("0")
            precio_vta = dec(presentacion.precio_venta or 0)

            # Idempotencia por (producto, presentación, origen INVENTARIO_INICIAL)
            lote_existente = db.execute(
                select(LoteInventario).where(
                    LoteInventario.producto_id == producto.id,
                    LoteInventario.almacen_id == almacen.id,
                    LoteInventario.presentacion_principal_id == presentacion.id,
                    LoteInventario.origen == "INVENTARIO_INICIAL",
                )
            ).scalar_one_or_none()
            if lote_existente is not None:
                continue

            lote = servicio_lotes.crear_lote(
                db,
                producto_id=producto.id,
                almacen_id=almacen.id,
                cantidad_base=cantidad_base,
                cantidad_inicial=cantidad_base,
                costo_base=costo_base,
                costo_unitario=q2(costo_ref),
                costo_transporte=Decimal("0"),
                precio_venta=q2(precio_vta),
                presentacion_id=presentacion.id,
                fecha_ingreso=date.today(),
                usuario_id=usuario_id,
                origen="INVENTARIO_INICIAL",
            )
            inventario.aplicar_entrada(
                db,
                almacen_id=almacen.id,
                producto_id=producto.id,
                cantidad_base=cantidad_base,
                costo_unitario_base=costo_base,
                tipo=TipoMovimiento.SALDO_INICIAL,
                origen_tipo="INVENTARIO_INICIAL",
                origen_id=0,
                usuario_id=usuario_id,
                referencia="Inventario físico tienda",
                lote_id=lote.id,
            )
            lotes_creados += 1

    db.commit()
    return {
        "lineas_lista": len(ITEMS_INVENTARIO_TIENDA),
        "fusiones": fusiones,
        "productos_nuevos": nuevos,
        "productos_actualizados": actualizados,
        "lotes_iniciales": lotes_creados,
        "lineas_sin_stock": sin_stock,
    }


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Carga el catálogo y conteo físico de inventario_tienda.md."
    )
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Muestra el resumen sin escribir en la base de datos.",
    )
    args = analizador.parse_args()

    db = SessionLocal()
    try:
        resumen = cargar_inventario_tienda(db, simular=args.simular)
    finally:
        db.close()

    encabezado = "SIMULACIÓN" if args.simular else "Inventario de la tienda cargado"
    print(f"{encabezado}:")
    print(f"  Líneas procesadas:      {resumen['lineas_lista']}")
    print(f"  Duplicados fusionados:  {resumen['fusiones']}")
    print(f"  Productos nuevos:       {resumen['productos_nuevos']}")
    print(f"  Productos actualizados: {resumen['productos_actualizados']}")
    print(f"  Lotes con stock creados:{resumen['lotes_iniciales']}")
    print(f"  Líneas sin stock (0/—): {resumen['lineas_sin_stock']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
