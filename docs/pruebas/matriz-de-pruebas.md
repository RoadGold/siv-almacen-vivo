# Pruebas y criterios de calidad · SIV · Almacén Vivo

## 1. Códigos de la API

| # | Escenario | Dónde se verifica | Estado |
|---|---|---|---|
| T01 | Crear producto con una presentación | `test_flujo_completo.py::test_t01` | ✅ |
| T02 | Duplicar código interno rechazado | `test_t02` | ✅ |
| T03 | Dos proveedores para un mismo producto | `test_t03` | ✅ |
| T04 | 5 cajas × 24 = +120 unidades | `test_t04` | ✅ |
| T05 | 3 sacos × 50 kg = +150 000 g | `test_t05` (incluye costo base 0,0034) | ✅ |
| T06 | Venta de 0,750 kg = −750 g | `test_t06` | ✅ |
| T07 | Venta de 0,5 unidad indivisible rechazada | `test_t07` | ✅ |
| T08 | Venta por encima del stock rechazada | `test_t08` | ✅ |
| T09 | Dos vendedores disputan la última unidad | `test_concurrencia.py::test_t09` | ✅ |
| T10 | Doble confirmación = una sola venta | `test_t10` | ✅ |
| T11 | Fallo al crear el movimiento revierte todo | `test_concurrencia.py::test_t11` | ✅ |
| T12 | Anular restituye stock y conserva la huella | `test_t12` | ✅ |
| T13 | Anular dos veces rechazado | `test_t13` | ✅ |
| T14 | Cambiar el precio no altera ventas pasadas | `test_t14` | ✅ |
| T15 | Cambiar el factor no altera el historial | `test_t15` | ✅ |
| T16 | Permisos validados en el servidor | `test_t16` (2 casos) | ✅ |
| T17 | Producto desactivado conserva el histórico | `test_t17` | ✅ |
| T18 | Importación Excel con vista previa y sin altas silenciosas | `test_importador.py::test_t18` | ✅ |
| T19 | Restauración de un respaldo | `scripts/restaurar/restaurar.ps1` + `scripts/respaldo/crear-respaldo.ps1` (ensayo manual realizado) | ✅ |
| T20 | Operar sin Internet | Diseño local (sin CDN ni servicios externos) | ✅ (revisión manual) |

Pruebas adicionales: conversiones y costos (`test_dominio.py`), ajustes administrativos,
conciliación, carga de inventario inicial y plantilla de importación.

## 2. Cómo ejecutar

```powershell
# Base de datos de pruebas en memoria (rápida y desechable)
docker compose --profile test up -d db-test

cd backend
.\.venv\Scripts\python.exe -m pytest app/tests -q      # 32 pruebas, ~7 s
```

```powershell
# Frontend
cd frontend
npm install
npm test          # pruebas de aritmética decimal y formatos
npm run build     # compilación de producción
```

## 3. Recorrido de aceptación (extremo a extremo)

Con el servidor en marcha (`http://127.0.0.1:8000`):

```powershell
& ".\backend\.venv\Scripts\python.exe" "scripts\pruebas\recorrido_aceptacion.py" --usuario admin --password "mi-clave"
```

Cubre el recorrido del plan §17 completo: proveedor → productos (a granel y unitario) →
abastecimiento → conversión exacta → venta fraccionada → venta por caja → stock y huella →
idempotencia → anulación con reverso → conciliación y persistencia.

**Última ejecución:** todas las comprobaciones correctas.

## 4. Rendimiento

| Acción | Objetivo | Cómo verificar |
|---|---|---|
| Búsqueda de producto | p95 ≤ 500 ms en entorno local | `GET /api/v1/catalogo/productos?q=…` con 10 000 productos |
| Confirmación de venta simple | p95 ≤ 1 s | `POST /api/v1/ventas` |
| Listado paginado | No descarga el catálogo completo | Todas las listas usan `pagina`/`tamano` |

Pendiente: generar el conjunto de datos de prueba (10 000 productos · 500 proveedores ·
100 000 ventas · 500 000 movimientos) y registrar los tiempos en el equipo real.

## 5. Criterios de calidad pendientes

- [ ] Pruebas E2E de interfaz (Playwright) sobre VENDER y RECIBIR.
- [ ] Medición de rendimiento con el conjunto de datos masivo.
- [ ] Prueba de restauración automática de respaldo en la versión final del empaquetado.
- [ ] Revisión de accesibilidad con lector de pantalla en las pantallas de venta.
