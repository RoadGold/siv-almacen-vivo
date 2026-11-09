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
| Fase 4 · Productos, unidades y presentaciones | ✅ API completa · interfaz en curso |
| Fase 5 · Proveedores | ✅ API completa · interfaz en curso |
| Fase 6 · Abastecimiento desde proveedor | ✅ API completa (previsualización, confirmación, reversión) |
| Fase 7 · Punto de venta | ✅ API completa (carrito, idempotencia, control de concurrencia) |
| Fase 8 · Exploración, kardex y radar | ✅ API completa (ficha viva, radar, conciliación) |
| Fase 9 · Reportes e indicadores | ✅ API completa (ventas, costos, valorización, margen bruto, exportación CSV) · interfaz en curso |
| Fase 10 · Seguridad, roles y respaldo | 🔄 Roles, auditoría y scripts de respaldo listos; falta endurecer sesiones y respaldo programado |
| Fase 11 · Pruebas, empaquetado y puesta en marcha | 🔄 En curso (37 pruebas automatizadas en verde + recorrido de aceptación E2E) |

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

Cobertura actual: **37 pruebas** que incluyen conversiones exactas (caja × 24, saco de 50 kg,
venta fraccionada de 0,750 kg), rechazo de fracciones en productos indivisibles, stock
insuficiente, idempotencia, concurrencia sobre la última unidad, atomicidad de la transacción,
reversión por anulación, snapshots históricos, permisos por rol, importación de Excel y reportes.

Recorrido de aceptación contra el sistema en marcha:

```powershell
& ".\backend\.venv\Scripts\python.exe" "scripts\pruebas\recorrido_aceptacion.py" --usuario admin --password "mi-clave"
```

Conjunto de datos ficticio para pruebas de rendimiento (10 000 productos · 500 proveedores ·
100 000 ventas): `backend\.venv\Scripts\python.exe -m app.cli.datos_carga`.

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
| `docs/manuales/usuario.md` | Manual corto de operación |
| `PLAN_DESARROLLO_SIV_ALMACEN_VIVO.md` | Plan maestro del proyecto |

---

## Notas de operación

- El servidor escucha solo en `127.0.0.1`. Para varias computadoras en red local, revise la sección
  13.2 del plan antes de habilitar el acceso por LAN.
- Los comprobantes generados en V1 son **internos** y no sustituyen los comprobantes tributarios
  exigibles.
- Para la puesta en producción se recomienda PostgreSQL nativo en el equipo del negocio (ver
  AD-13 en `docs/arquitectura/decisiones.md`).
