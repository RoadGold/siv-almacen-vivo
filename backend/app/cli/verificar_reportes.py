"""Comprobación de los reportes de Analizar sobre la base de trabajo (solo lectura).

Verifica que los endpoints que fallaban (500) respondan y devuelvan datos:
inventario por lote, ventas por lote, histórico de costos, inventario
valorizado, ventas por periodo y abastecimientos por proveedor.

Uso:  python -m app.cli.verificar_reportes
"""

from __future__ import annotations

import sys

from app.db.session import SessionLocal
from app.services import reportes as servicio


def main() -> int:
    db = SessionLocal()
    try:
        inventario = servicio.inventario_por_lote(db, limite=5000)
        con_stock = [f for f in inventario if f["estado"] != "AGOTADO"]
        agotados = [f for f in inventario if f["estado"] == "AGOTADO"]
        valor = sum(float(f["valor_costo"]) for f in inventario)
        print(f"[1] Inventario por lote: {len(inventario)} lotes ({len(con_stock)} con stock, {len(agotados)} agotados)")
        print(f"    Valor total al costo: {valor:.2f}")
        if inventario:
            fila = con_stock[0] if con_stock else inventario[0]
            print(f"    Ejemplo: {fila['codigo_lote']} {fila['producto_nombre']}")
            print(f"      presentacion={fila['presentacion_nombre']} factor={fila['factor_base']}")
            print(f"      stock={fila['cantidad_disponible']} g = {fila['cantidad_disponible_presentacion']} x presentacion")
            print(f"      costo_unitario={fila['costo_unitario']} transporte={fila['costo_transporte']} precio={fila['precio_venta']}")

        por_producto = servicio.ventas_por_producto(db, limite=100)
        print(f"[2] Ventas por producto: {len(por_producto)} filas")

        costos = servicio.historico_de_costos(db, limite=5000)
        print(f"[3] Historico de costos: {len(costos)} filas")
        if costos:
            print(f"    Ejemplo: {costos[0]['producto']} / {costos[0]['presentacion']} "
                  f"costo={costos[0]['costo_unitario']} transporte={costos[0]['costo_transporte']}")

        valorizado = servicio.inventario_valorizado(db)
        print(f"[4] Inventario valorizado: {len(valorizado)} productos")

        periodo = servicio.ventas_por_periodo(db)
        print(f"[5] Ventas del periodo: {periodo['operaciones']} operaciones, total {periodo['total']}")

        proveedores = servicio.abastecimientos_por_proveedor(db)
        print(f"[6] Abastecimientos por proveedor: {len(proveedores)} proveedores")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
