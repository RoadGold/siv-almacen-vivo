# SIV · Almacén Vivo — Frontend

Interfaz web de **SIV · Almacén Vivo**:React + TypeScript + Vite + Tailwind CSS v3 + TanStack Query.

La interfaz está organizada por tareas (plan maestro §2): tres estaciones de trabajo
(**VENDER**, **RECIBIR**, **EXPLORAR**) más una banda secundaria de herramientas
(**Analizar**, **Gestionar**, **Administrar**).

---

## 1. Requisitos

| Herramienta | Versión mínima | Notas |
|---|---|---|
| Node.js | 18 | La instalación actual usa 18.18.0 |
| npm | 9 | Se instala junto con Node |
| Backend SIV | — | Debe estar encendido en `http://127.0.0.1:8000` |

No se usa ninguna CDN: tipografías del sistema, Tailwind local y todas las dependencias
instaladas con npm. El sistema funciona sin conexión a internet.

## 2. Instalación

```bash
cd frontend
npm install
```

## 3. Desarrollo

```bash
npm run dev      # http://127.0.0.1:5173
```

El servidor de Vite escucha en `127.0.0.1:5173`. El backend acepta ese origen en
`ALLOWED_ORIGINS` (`http://127.0.0.1:5173`), por lo que no hace falta configurar nada
para las peticiones entre el navegador y la API.

### Configuración

Copia el archivo de ejemplo y ajústalo si el backend no está en la ruta habitual:

```bash
cp .env.example .env      # en Windows: copy .env.example .env
```

```env
# frontend/.env
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

| Variable | Por defecto | Descripción |
|---|---|---|
| `VITE_API_URL` | `http://127.0.0.1:8000/api/v1` | URL base de la API (sin barra final) |

## 4. Compilación de producción

```bash
npm run build     # comprueba tipos con tsc y genera frontend/dist
npm run preview   # sirve localmente lo compilado (opcional)
```

La salida queda en `frontend/dist`. El backend la sirve estáticamente:

```python
# backend/app/main.py
FRONTEND_DIR = Path(__file__).resolve().parents[2].parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
```

Con la compilación presente, la aplicación completa queda disponible en
**http://127.0.0.1:8000** (interfaz) y la API en **http://127.0.0.1:8000/api/v1**
(documentación interactiva en http://127.0.0.1:8000/api/docs).

> **Nota sobre el enrutado:** se usa `HashRouter` (`http://127.0.0.1:8000/#/vender`) porque
> `StaticFiles(html=True)` no aplica el «fallback» de las aplicaciones de una sola página:
> sin hash, recargar en `/vender` devolvería un 404. Si el backend añade una ruta comodín
> que devuelva `index.html` para las rutas del SPA, basta cambiar `HashRouter` por
> `BrowserRouter` en `src/main.tsx` (no hay ningún otro cambio pendiente).

## 5. Otros comandos

```bash
npm test         # pruebas unitarias de la aritmética decimal y los formatos (Vitest)
npm run typecheck  # comprobación de tipos sin generar la compilación
```

## 6. Pantallas

| Ruta | Pantalla | Contenido |
|---|---|---|
| `/login` | Acceso | Usuario y contraseña; guarda token y datos del usuario |
| `/` | Inicio | Saludo, tres tarjetas de estación, «Hoy en la tienda», «Atención necesaria», «Actividad reciente» |
| `/vender` | Vender | Buscador + carrito editable, cinta de impacto, previsualización y confirmación idempotente |
| `/recibir` | Recibir | Ingreso en tres pasos: proveedor → productos → revisar y confirmar |
| `/explorar` | Explorar | Existencias con filtros, ficha viva del producto y radar de reposición |
| `/kardex` | Kardex | Movimiento completo con filtros (producto, tipo, fechas) y paginación en el servidor |
| `/gestionar/productos` | Productos | Catálogo paginado, alta con presentaciones, edición e **importación desde Excel** |
| `/gestionar/proveedores` | Proveedores | Directorio paginado, alta, edición y vinculación de productos |
| `/analizar` | Analizar | Reportes del periodo, margen bruto estimado, inventario valorizado y exportación CSV |
| `/administrar` | Administrar | Usuarios y roles, auditoría y diagnóstico del servidor local |

### Atajos de teclado

| Atajo | Acción |
|---|---|
| `F3` | Enfocar el buscador (pantalla Vender) |
| `Esc` | Limpiar la búsqueda (pantalla Vender) o cerrar un modal |
| `Tab` / `Shift + Tab` | Navegación completa; el foco queda atrapado dentro de los modales |
| `Enter` | En el buscador: si el texto es un código de barras, añade el producto exacto |

## 7. Decisiones técnicas

### Importes y cantidades sin coma flotante

La API devuelve **todos** los importes y cantidades como cadenas decimales. El frontend
nunca usa `parseFloat` ni suma `number` para dinero: la utilidad
`src/shared/format/decimal.ts` implementa una clase `Decimal` basada en enteros grandes
(`bigint`) con escala explícita, con operaciones `suma`, `resta`, `multiplica` y
`redondear` (mitad hacia arriba) exactas. Los importes se formatean con coma decimal y
separador de miles peruano (`S/ 1 234,50`).

### Formatos locales

`src/shared/format/formato.ts` centraliza la convención peruana: moneda `S/`, coma decimal,
separador de miles con espacio fino, fechas `dd/mm/aaaa` y expresiones legibles de stock
(`45,500 kg`, `208 unidades`, `750 g`).

### Cliente HTTP

`src/shared/api/client.ts`:

- URL base configurable con `VITE_API_URL`.
- `Authorization: Bearer <token>` leído del almacén de sesión en `localStorage`.
- Normaliza el sobre de error `{ "error": { "codigo", "mensaje", "detalle" } }` del backend
  en la clase `ErrorApi` (`codigo`, `mensaje`, `detalle`, `estado`), y también el
  `{ "detail": ... }` de FastAPI.
- Un `401` con token previo cierra la sesión y devuelve al usuario a `/login`.

### Sesión y permisos

El token y los datos del usuario se guardan en `localStorage` (`siv.token`, `siv.usuario`).
La interfaz oculta lo que el usuario no tiene permitido, pero **el servidor es la
autoridad**: un `403` se muestra como estado «sin permisos» aunque el botón se muestre.
La banda secundaria se arma con los permisos del usuario: «Analizar» requiere
`reportes.ver`, «Kardex» `inventario.ver` y «Administrar» cualquiera de `admin.usuarios`
o `admin.auditoria`.

### Descargas e importaciones

- `src/shared/api/client.ts` incorpora dos funciones que el cliente JSON no cubre:
  `descargar()` (respuesta binaria) y `enviarFormulario()` (`multipart/form-data`).
- `src/shared/utils/descargas.ts` guarda el `Blob` en disco con un nombre de archivo
  derivado del periodo, sin CDN ni dependencias externas.
- La importación de catálogo **nunca** se aplica sin una confirmación explícita: primero
  se previsualiza el archivo (resumen y errores por fila) y solo después el usuario
  decide confirmar. La opción de aplicar el stock inicial viene desmarcada por defecto.

### Idempotencia

Cada confirmación de venta se envía con una `idempotency_key` UUID nueva. El botón queda
bloqueado mostrando «Registrando venta…» mientras la petición está en curso, de modo que
un doble clic no puede duplicar la operación; el backend también rechaza la repetición.

### Identidad visual

Los tokens están en `src/design-system/tokens.css` y se consumen desde
`tailwind.config.js`. El color nunca es la única señal: cada estado incluye la palabra
«Agotado», «Bajo mínimo» o «Disponible». Se respetan `prefers-reduced-motion`,
`prefers-contrast` y el foco visible en todos los controles.

### Estructura

```text
frontend/src/
├── app/                    # rutas, proveedores globales y layout (barra de pulso, navegación)
├── design-system/          # tokens y componentes base (Button, Input, Table, Modal, …)
├── features/
│   ├── acceso/             # login
│   ├── inicio/             # pantalla inicial orientada a tareas
│   ├── vender/             # punto de venta
│   ├── recibir/            # ingreso de mercadería en tres pasos
│   ├── explorar/           # existencias, ficha viva y radar de reposición
│   ├── kardex/             # movimiento completo del inventario
│   ├── productos/          # catálogo e importación desde Excel
│   ├── proveedores/        # directorio de proveedores
│   ├── analizar/           # reportes del periodo
│   ├── administracion/     # usuarios, auditoría y diagnóstico
│   └── comunes/            # pantalla de ruta inexistente
└── shared/
    ├── api/                # cliente HTTP, endpoints y claves de caché
    ├── auth/               # almacén de sesión y proveedor de autenticación
    ├── estado/             # registro de la última operación
    ├── format/             # decimal.ts y formato.ts (+ pruebas)
    ├── hooks/              # utilidades de consulta y errores
    ├── types/              # contratos del API
    └── utils/              # descargas de archivos (+ pruebas)
```

## 8. Limitaciones conocidas

1. **Código de barras:** el backend no expone un índice por `codigo_barras`, así que la
   búsqueda exacta recorre las páginas del catálogo activo
   (`src/features/vender/buscarCodigoBarras.ts`). Con el catálogo previsto (1 000–10 000
   productos) es rápido, pero un endpoint dedicado sería mejor.
2. **Nombres en el kardex:** `/inventario/movimientos` solo devuelve `producto_id`; la
   interfaz resuelve el nombre con una consulta por producto (cacheada por TanStack Query).
3. **Histórico de costos:** `/reportes/costos` no admite paginación (el servidor limita a
   500 filas); la tabla se muestra con desplazamiento vertical.
4. **Inventario inicial:** el backend ya expone `POST /inventario/inventario-inicial`, pero
   la interfaz no tiene todavía una pantalla de carga inicial: hoy se hace con el
   «stock inicial» de la importación de catálogo o con ajustes administrativos.
5. **Sin conexión a internet:** si la API no responde, la barra de pulso muestra
   «Servidor local sin conexión» y cada pantalla explica qué ocurrió.

## 9. Qué debe revisar el responsable del proyecto

- Confirmar la convención de separador de miles (espacio fino) y el nombre de la
  estación «EXPLORAR».
- Decidir si se mantiene `HashRouter` o se añade el «fallback» de SPA al backend y se
  cambia a `BrowserRouter`.
- Revisar si el CSV de ventas necesita más columnas (cliente, estado de anulación) o un
  formato distinto al separador `;`.
- Validar el copy de los estados vacíos y de los mensajes de error de negocio.
- Decidir si la exportación CSV debe ofrecer también un Excel (`.xlsx`) del reporte.
- Revisar quién puede ver «Administrar → Diagnóstico»: hoy lo ven los usuarios con
  `admin.usuarios` o `admin.auditoria`.
