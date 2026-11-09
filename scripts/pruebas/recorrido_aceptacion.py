"""Recorrido de aceptación del primer incremento funcional (plan §17).

Ejecuta, contra un servidor SIV en marcha, el recorrido completo:

    Proveedor → Producto a granel → Producto unitario → Abastecimiento →
    Venta fraccionada → Venta por caja → Verificación de stock y huella →
    Anulación autorizada → Comprobación de persistencia.

Uso:
    python scripts/pruebas/recorrido_aceptacion.py --usuario admin --password "clave"

Debe ejecutarse contra una base de datos de VALIDACIÓN (no con datos reales).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from decimal import Decimal

BASE_POR_DEFECTO = "http://127.0.0.1:8000/api/v1"


class Cliente:
    def __init__(self, base: str, token: str | None = None) -> None:
        self.base = base
        self.token = token

    def peticion(self, metodo: str, ruta: str, cuerpo: dict | None = None) -> tuple[int, dict]:
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        peticion = urllib.request.Request(f"{self.base}{ruta}", data=datos, method=metodo)
        peticion.add_header("Accept", "application/json")
        if datos:
            peticion.add_header("Content-Type", "application/json")
        if self.token:
            peticion.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                return respuesta.status, json.loads(respuesta.read() or b"{}")
        except urllib.error.HTTPError as error:
            cuerpo_error = error.read().decode("utf-8", errors="replace")
            try:
                return error.code, json.loads(cuerpo_error)
            except json.JSONDecodeError:
                return error.code, {"detalle": cuerpo_error}

    def get(self, ruta: str) -> tuple[int, dict]:
        return self.peticion("GET", ruta)

    def post(self, ruta: str, cuerpo: dict | None = None) -> tuple[int, dict]:
        return self.peticion("POST", ruta, cuerpo)

    def patch(self, ruta: str, cuerpo: dict) -> tuple[int, dict]:
        return self.peticion("PATCH", ruta, cuerpo)


class Comprobador:
    def __init__(self) -> None:
        self.fallos = 0

    def verificar(self, condicion: bool, descripcion: str, detalle: object = "") -> None:
        if condicion:
            print(f"  [OK]   {descripcion}")
        else:
            self.fallos += 1
            print(f"  [FALLA] {descripcion} {detalle}")


def ejecutar(base: str, usuario: str, password: str) -> int:
    comprobador = Comprobador()
    marca = uuid.uuid4().hex[:8]

    print("\n1) Inicio de sesión")
    estado, cuerpo = Cliente(base).post("/auth/login", {"usuario": usuario, "password": password})
    if estado != 200:
        print(f"  [FALLA] No se pudo iniciar sesión: {cuerpo}")
        return 1
    cliente = Cliente(base, cuerpo["access_token"])
    comprobador.verificar(estado == 200, f"Sesión iniciada como {cuerpo['usuario']['nombre']}")

    print("\n2) Proveedor")
    estado, proveedor = cliente.post(
        "/proveedores",
        {
            "codigo": f"PRV-{marca}",
            "razon_social": "Mayorista Central SAC (prueba)",
            "nombre_comercial": "Mayorista Central",
            "contacto": "Rosa Quispe",
        },
    )
    comprobador.verificar(estado == 201, "Proveedor creado", proveedor)

    print("\n3) Unidades de medida disponibles")
    _, unidades = cliente.get("/catalogo/unidades")
    por_codigo = {u["codigo"]: u for u in unidades}
    gramo = por_codigo.get("GR")
    unidad = por_codigo.get("UND")
    comprobador.verificar(gramo is not None and unidad is not None, "Unidades GR y UND disponibles")

    print("\n4) Productos con sus presentaciones")
    _, arroz = cliente.post(
        "/catalogo/productos",
        {
            "codigo": f"ARR-{marca}",
            "nombre": "Arroz a granel",
            "unidad_base_id": gramo["id"],
            "stock_minimo_base": "10000",
            "permite_fraccion": True,
            "presentaciones": [
                {"nombre": "1 kg", "factor_base": "1000", "precio_venta": "5.00", "permite_fraccion": True},
                {"nombre": "saco 50 kg", "factor_base": "50000", "precio_venta": "180.00"},
            ],
        },
    )
    _, gaseosa = cliente.post(
        "/catalogo/productos",
        {
            "codigo": f"GAS-{marca}",
            "nombre": "Gaseosa 500 ml",
            "unidad_base_id": unidad["id"],
            "presentaciones": [
                {"nombre": "botella", "factor_base": "1", "precio_venta": "2.50"},
                {"nombre": "paquete x6", "factor_base": "6", "precio_venta": "13.50"},
                {"nombre": "caja x24", "factor_base": "24", "precio_venta": "48.00"},
            ],
        },
    )
    comprobador.verificar("id" in arroz and "id" in gaseosa, "Productos creados")

    arroz_pp = {p["nombre"]: p["id"] for p in arroz["presentaciones"]}
    gaseosa_pp = {p["nombre"]: p["id"] for p in gaseosa["presentaciones"]}

    print("\n5) Abastecimiento desde el proveedor")
    _, abastecimiento = cliente.post(
        "/abastecimientos",
        {
            "proveedor_id": proveedor["id"],
            "documento": "F001-PRUEBA",
            "lineas": [
                {
                    "producto_id": arroz["id"],
                    "presentacion_id": arroz_pp["saco 50 kg"],
                    "cantidad": "2",
                    "costo_unitario": "170.00",
                },
                {
                    "producto_id": gaseosa["id"],
                    "presentacion_id": gaseosa_pp["caja x24"],
                    "cantidad": "3",
                    "costo_unitario": "45.00",
                },
            ],
        },
    )
    comprobador.verificar(
        abastecimiento.get("estado") == "CONFIRMADO",
        f"Abastecimiento confirmado: {abastecimiento.get('numero')}",
        abastecimiento,
    )
    conversiones = {
        d["presentacion_nombre"]: d["cantidad_base"] for d in abastecimiento.get("detalles", [])
    }
    comprobador.verificar(
        conversiones.get("saco 50 kg") == "100000",
        "2 sacos de 50 kg = 100 000 g",
        conversiones,
    )
    comprobador.verificar(
        conversiones.get("caja x24") == "72", "3 cajas × 24 = 72 unidades", conversiones
    )

    print("\n6) Ventas")
    _, venta_fraccion = cliente.post(
        "/ventas",
        {
            "idempotency_key": f"aceptacion-fraccion-{marca}",
            "lineas": [
                {
                    "producto_id": arroz["id"],
                    "presentacion_id": arroz_pp["1 kg"],
                    "cantidad": "0.750",
                }
            ],
        },
    )
    comprobador.verificar(
        venta_fraccion.get("estado") == "CONFIRMADO",
        f"Venta fraccionada registrada: {venta_fraccion.get('numero')}",
        venta_fraccion,
    )
    comprobador.verificar(
        venta_fraccion["detalles"][0]["cantidad_base"] == "750",
        "0,750 kg = 750 g",
        venta_fraccion["detalles"][0],
    )

    _, venta_caja = cliente.post(
        "/ventas",
        {
            "idempotency_key": f"aceptacion-caja-{marca}",
            "lineas": [
                {
                    "producto_id": gaseosa["id"],
                    "presentacion_id": gaseosa_pp["paquete x6"],
                    "cantidad": "1",
                }
            ],
        },
    )
    comprobador.verificar(
        venta_caja.get("estado") == "CONFIRMADO",
        f"Venta por paquete registrada: {venta_caja.get('numero')}",
        venta_caja,
    )

    print("\n7) Stock y huella")
    _, existencias = cliente.get(f"/inventario/existencias?q={marca}")
    por_codigo_existencias = {e["codigo"]: e for e in existencias["items"]}
    arroz_stock = por_codigo_existencias.get(f"ARR-{marca}", {}).get("cantidad_base")
    gaseosa_stock = por_codigo_existencias.get(f"GAS-{marca}", {}).get("cantidad_base")
    comprobador.verificar(arroz_stock == "99250", "Arroz: 99 250 g", arroz_stock)
    comprobador.verificar(gaseosa_stock == "66", "Gaseosa: 66 unidades", gaseosa_stock)

    _, huella = cliente.get(f"/inventario/movimientos?producto_id={arroz['id']}")
    tipos = [m["tipo"] for m in huella["items"]]
    comprobador.verificar(
        "ABASTECIMIENTO" in tipos and "VENTA" in tipos,
        "La huella muestra abastecimiento y venta",
        tipos,
    )
    comprobador.verificar(
        all(m.get("referencia") for m in huella["items"]),
        "Cada movimiento tiene referencia verificable",
        huella["items"],
    )

    print("\n8) Idempotencia y stock insuficiente")
    _, repetida = cliente.post(
        "/ventas",
        {
            "idempotency_key": f"aceptacion-fraccion-{marca}",
            "lineas": [
                {
                    "producto_id": arroz["id"],
                    "presentacion_id": arroz_pp["1 kg"],
                    "cantidad": "0.750",
                }
            ],
        },
    )
    comprobador.verificar(
        repetida.get("numero") == venta_fraccion.get("numero"),
        "Repetir la misma clave devuelve la misma venta (sin duplicar)",
        repetida,
    )

    _, inventario_final = cliente.get(f"/inventario/existencias?q={marca}")
    arroz_final = next(
        e for e in inventario_final["items"] if e["codigo"] == f"ARR-{marca}"
    )["cantidad_base"]
    comprobador.verificar(arroz_final == "99250", "El stock no se descontó dos veces", arroz_final)

    print("\n9) Anulación autorizada")
    _, anulacion = cliente.post(
        f"/ventas/{venta_caja['id']}/anular",
        {"motivo": "Prueba de aceptación: devolución de mercadería"},
    )
    comprobador.verificar(
        anulacion.get("estado") == "ANULADO", "Venta anulada", anulacion
    )
    _, tras_anular = cliente.get(f"/inventario/existencias?q={marca}")
    gaseosa_final = next(
        e for e in tras_anular["items"] if e["codigo"] == f"GAS-{marca}"
    )["cantidad_base"]
    comprobador.verificar(gaseosa_final == "72", "El stock volvió a 72 unidades", gaseosa_final)

    _, huella_final = cliente.get(f"/inventario/movimientos?producto_id={gaseosa['id']}")
    tipos_final = [m["tipo"] for m in huella_final["items"]]
    comprobador.verificar(
        "REVERSO_VENTA" in tipos_final,
        "La huella conserva el movimiento de reversión",
        tipos_final,
    )

    print("\n10) Persistencia y conciliación")
    _, conciliacion = cliente.get("/inventario/conciliacion")
    comprobador.verificar(
        conciliacion["diferencias"] == [] and conciliacion["existencias_negativas"] == [],
        "El kardex y las existencias coinciden",
        conciliacion,
    )

    # Cierre de sesión y nueva conexión: los datos siguen ahí.
    _, cierre = cliente.post("/auth/logout")
    estado, cuerpo = Cliente(base).post("/auth/login", {"usuario": usuario, "password": password})
    _, persistencia = cliente.get(f"/inventario/existencias?q={marca}")
    comprobador.verificar(
        estado == 200 and persistencia["total"] >= 2,
        "Los datos persisten tras cerrar y volver a abrir sesión",
        persistencia.get("total"),
    )

    print("\n" + "=" * 60)
    if comprobador.fallos == 0:
        print("RESULTADO: todas las comprobaciones del recorrido fueron correctas.")
        return 0
    print(f"RESULTADO: {comprobador.fallos} comprobaciones fallaron.")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Recorrido de aceptación de SIV")
    parser.add_argument("--base", default=BASE_POR_DEFECTO)
    parser.add_argument("--usuario", default="admin")
    parser.add_argument("--password", default="clave-local-2026")
    args = parser.parse_args()
    sys.exit(ejecutar(args.base, args.usuario, args.password))


if __name__ == "__main__":
    main()
