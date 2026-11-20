# SIV · Almacén Vivo

Sistema web local de inventario, proveedores, abastecimiento y ventas para una tienda de abarrotes.

**Proveedor → Abastecimiento → Existencias → Venta → Movimiento auditado → Reporte.**

Funciona sin Internet. Todo el stack se ejecuta en el equipo del negocio.

---

## Estado actual del proyecto

| Fase del plan | Estado |
|---|---|
| Fase 0 · Descubrimiento y reglas operativas | ✅ Completada (`docs/requisitos/especificacion-funcional.md`) |
| Fase 1 · Diseño UX/UI | 🔄 En curso (prototipo navegable en `frontend/`) |
| Fase 2 · Fundación técnica | ✅ Completada (FastAPI + React + PostgreSQL + Docker + pruebas) |
| Fase 3 · Modelo de datos y motor de inventario | ✅ Completada (migraciones, existencias, kardex, costo promedio, conciliación) |
| Fase 4 · Productos, unidades y presentaciones | ✅ Catálogo, presentaciones, importación Excel con vista previa |
| Fase 5 · Proveedores | ✅ Alta, productos habituales, costos e historial |
| Fase 6 · Abastecimiento desde proveedor | ✅ Flujo de 3 pasos, previsualización, confirmación y reversión. **Cada línea crea un lote con su precio de venta** |
| Fase 7 · Punto de venta | ✅ Carrito, cinta de impacto, idempotencia, concurrencia, **precios variables con límite de descuento**, **selección de lote (PEPS)**, **cobro** (forma de pago, recibido, vuelto) e **impresión del ticket** |
| Fase 8 · Exploración, kardex y radar | ✅ Ficha viva con **panel de lotes**, radar, conciliación y **pantalla de kardex** |
| Fase 9 · Reportes e indicadores | ✅ Ventas, costos, valorización, margen bruto, exportación CSV y **pantalla Analizar** |
| Fase 10 · Seguridad, roles y respaldo | ✅ Roles, auditoría (incluidos los cambios de precio), **configuración del negocio**, respaldo y restauración |
| Fase 11 · Pruebas, empaquetado y puesta en marcha | 🔄 En curso (233 pruebas de backend y 66 de frontend en verde + recorrido de aceptación E2E). **Pendiente**: empaquetador para Windows y prueba física de la impresora |

---

## Estructura del repositorio

```text
siv-almacen-vivo/
├── backend/                 # API FastAPI (Python 3.11)
│   ├── app/
│   │   ├── api/v1/routers/  # endpoints
│   │   ├── core/            # configuración, seguridad, permisos, errores
│   │   ├── domain/          # reglas puras: conversiones y costos
│   │   ├── services/        # casos de uso (inventario, ventas, abastecimientos…)
│   │   ├── db/              # modelos SQLAlchemy y sesión
│   │   ├── schemas/         # contratos Pydantic
│   │   ├── cli/             # instalación, datos de ejemplo, limpieza
│   │   └── tests/           # pytest
│   ├── alembic/             # migraciones versionadas
│   └── pyproject.toml
├── frontend/                # React + TypeScript + Vite + Tailwind
├── docs/                    # requisitos, arquitectura, manuales, pruebas
├── scripts/                 # instalar, iniciar, respaldo, restaurar
├── compose.yaml             # PostgreSQL + API (y base de pruebas en tmpfs)
└── .env.example
```

---

## Puesta en marcha (desarrollo)

### Requisitos

- Python 3.11+
- Node.js 18+
- Docker Desktop (solo para PostgreSQL en desarrollo)

### 1. Configurar el entorno

```powershell
Copy-Item .env.example .env
```

Ajuste `SECRET_KEY` y las credenciales de la base de datos.

### 2. Levantar todo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-local.ps1 -ConFrontend
```

El script levanta PostgreSQL, aplica las migraciones, arranca la API en
`http://127.0.0.1:8000` y el frontend de desarrollo en `http://127.0.0.1:5173`.

### 3. Instalación inicial del sistema

```powershell
& ".\backend\.venv\Scripts\python.exe" "scripts\instalar\instalar.py" --usuario admin --password "mi-clave-segura"
& ".\backend\.venv\Scripts\python.exe" "scripts\instalar\cargar_ejemplos.py"   # datos ficticios opcionales
```

Crea el usuario administrador, el almacén, las unidades de medida y las categorías básicas.

### 4. Entrar

- Frontend: <http://127.0.0.1:5173> (desarrollo) o <http://127.0.0.1:8000> (build)
- Documentación de la API: <http://127.0.0.1:8000/api/docs>

---

## Pruebas

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest app/tests -q
```

La base de pruebas vive en memoria (`tmpfs`) y se crea sola:

```powershell
docker compose --profile test up -d db-test
```

Cobertura actual: **320 pruebas** de backend (pytest) y **119** de frontend (Vitest), que incluyen
conversiones exactas (caja × 24, saco de 50 kg, venta fraccionada de 0,750 kg), rechazo de
fracciones en productos indivisibles, stock insuficiente, idempotencia, concurrencia sobre la
última unidad, atomicidad de la transacción, reversión por anulación, snapshots históricos,
**inventario por lotes (13 escenarios: lote inicial, ingreso que no toca el anterior, venta de
lote antiguo, venta de lote nuevo, venta combinada, stock insuficiente por lote, ajuste sobre un
lote, cambio de precio por lote, anulación con dos lotes, concurrencia, productos sin lotes,
código de barras y conciliación de existencias)**, precios variables y su límite de descuento,
impresión del ticket y su falla sin pérdida de la venta, permisos por rol, importación de Excel,
reportes, **contraste WCAG AA de las paletas clara y oscura**, **validaciones de los puntos de
entrada (deuda por cobrar, forma de pago cerrada, limpieza de campos al editar, RUC y correo
con formato, configuración del negocio e importación que respeta los schemas)** y el
**contrato de validaciones entre el backend y el cliente**.

### Validaciones: el backend manda, el cliente avisa

Las reglas de cada dato viven en los schemas del backend (`backend/app/schemas/`), que es la
única autoridad. El cliente aplica la misma regla para avisar antes de enviar, sin una ida y
vuelta al servidor.

Para que las dos capas no se separen, el backend **extrae** sus reglas de los schemas y las
publica en `frontend/src/shared/contrato/reglas.json`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.core.contrato_cli --escribir
```

Si se cambia una regla en el backend y no se regenera ese archivo, la prueba
`test_contrato_validaciones.py` falla. El cliente lee el contrato con
`@/shared/contrato/reglas` y lo usa en lugar de escribir las reglas a mano.

Recorrido de aceptación contra el sistema en marcha:

```powershell
& ".\backend\.venv\Scripts\python.exe" "scripts\pruebas\recorrido_aceptacion.py" --usuario admin --password "mi-clave"
```

Conjunto de datos ficticio para pruebas de rendimiento (10 000 productos · 500 proveedores ·
100 000 ventas): `backend\.venv\Scripts\python.exe -m app.cli.datos_carga`.

### Catálogo inicial de balanceados

El catálogo real del negocio (las listas de precios de VITAMAXPRO/INVITA y de TOMASINO) se
carga con un comando:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.datos_balanceados_cargar --simular   # ver qué se cargaría
.\.venv\Scripts\python.exe -m app.cli.datos_balanceados_cargar             # cargarlo
```

Qué hace:

- Crea los dos proveedores (**Vitamaxpro** y **Tomasino**) y las 12 categorías y 3 marcas.
- Carga **143 productos** con sus **189 presentaciones** (empaques). Un producto es un
  alimento; una presentación es un empaque («saco 40 kg pellet», «20 x 1 kg polvo»).
- El stock se lleva en **gramos**: un saco de 40 kg es un factor de 40 000.
- Los precios de las listas son **lo que paga el negocio**: se guardan como costo de
  referencia, y el precio de venta se calcula con el **margen del 30 %**.

Es **idempotente** y se puede volver a ejecutar cuando el distribuidor mande la lista
actualizada: los productos se reconocen por marca y nombre (y por el código del
distribuidor en TOMASINO), así que **ningún producto cambia de código** y no se rompe el
historial. Los productos que ya no están en la lista se **desactivan**, no se borran.

### Empezar de cero con el catálogo

Para dejar la base como recién instalada pero **con tu catálogo** (sin ventas, sin
ingresos, sin stock y sin los datos de ejemplo):

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.limpiar_operacion --simular   # ver qué se borra
.\.venv\Scripts\python.exe -m app.cli.limpiar_operacion             # limpiar
.\.venv\Scripts\python.exe -m app.cli.datos_balanceados_cargar       # rehacer los vínculos
```

Qué conserva: los usuarios y sus roles, el almacén, las unidades de medida y el catálogo
de balanceados. Qué borra: toda la operación (ventas, ingresos, movimientos, ajustes,
lotes, impresiones, auditoría) y los productos, proveedores, categorías y marcas de ejemplo.

Las secuencias se reinician, así que la primera venta es la **V-000001** y el primer
ingreso el **A-000001**.

---

## Respaldo y restauración

```powershell
powershell -ExecutionPolicy Bypass -File scripts\respaldo\crear-respaldo.ps1
powershell -ExecutionPolicy Bypass -File scripts\restaurar\restaurar.ps1 -Archivo respaldos\siv-20261109-001431.dump
```

Se usa `pg_dump`/`pg_restore` (nunca una copia de los archivos de datos). Cada respaldo incluye un
archivo `.info` con fecha y versión del esquema.

---

## Documentación

| Documento | Contenido |
|---|---|
| `docs/requisitos/especificacion-funcional.md` | Glosario, reglas, historias de usuario, casos de borde |
| `docs/arquitectura/API.md` | Contrato completo de la API |
| `docs/arquitectura/decisiones.md` | Decisiones técnicas y sus motivos |
| `docs/manuales/usuario.md` | Manual corto de operación para el personal |
| `docs/manuales/guia-usuario.md` | **Guía de usuario completa**: todas las pantallas, paso a paso |
| `docs/manuales/carga-inicial-catalogo.md` | **Carga inicial del catálogo** (productos que aún no tienen proveedor) |
| `docs/manuales/prueba-impresora.md` | **Prueba física de la impresora** (CBX-POS88E, ESC/POS) |
| `docs/manuales/administrador.md` | Guía técnica: instalación, respaldo, restauración, red local, diagnóstico |
| `docs/pruebas/matriz-de-pruebas.md` | Estado de los casos T01–T20 y criterios de calidad |
| `PLAN_DESARROLLO_SIV_ALMACEN_VIVO.md` | Plan maestro del proyecto |

---

## Notas de operación

- El servidor escucha solo en `127.0.0.1`. Para varias computadoras en red local, revise la sección
  13.2 del plan antes de habilitar el acceso por LAN.
- Los comprobantes generados en V1 son **internos** y no sustituyen los comprobantes tributarios
  exigibles.
- Para la puesta en producción se recomienda PostgreSQL nativo en el equipo del negocio (ver
  AD-13 en `docs/arquitectura/decisiones.md`).
