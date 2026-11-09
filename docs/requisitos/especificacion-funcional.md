# Especificación funcional · SIV · Almacén Vivo

> Fase 0 del plan de desarrollo. Cierra las reglas de inventario, el glosario, las
> historias de usuario y los casos de borde antes de seguir construyendo.

## 1. Glosario

| Término | Definición |
|---|---|
| **Unidad base** | Unidad en la que se acumula el stock de un producto: `unidad`, `gramo` o `mililitro`. Un producto tiene exactamente una. |
| **Presentación** | Forma comercial de un producto (botella, caja × 24, saco 50 kg, 1 kg). Cada presentación tiene un **factor de conversión** a la unidad base. |
| **Factor de conversión** | Número que multiplica la cantidad de presentación para obtener la cantidad en unidad base. Siempre mayor que cero. |
| **Cantidad base** | Cantidad expresada en la unidad base: `cantidad_presentación × factor_base`. |
| **Existencia** | Saldo actual de un producto en un almacén, expresado en unidad base. |
| **Costo promedio** | Costo por unidad base, calculado como promedio ponderado móvil. |
| **Abastecimiento** | Entrada de mercadería desde un proveedor. Siempre tiene proveedor, una o más líneas y un costo por línea. |
| **Venta** | Salida comercial. Es la **única** operación que resta stock por motivos comerciales. |
| **Reverso** | Contramovimiento que restituye el stock de una venta o retira el de un abastecimiento. Nunca borra la operación original. |
| **Ajuste administrativo** | Corrección de inventario por pérdida, rotura, vencimiento o diferencia de conteo. Va en auditoría y **no** es una venta. |
| **Huella** | Línea de tiempo de movimientos de un producto con su origen y responsable. |
| **Cinta de impacto** | Resumen, antes de confirmar, de exactamente qué stock cambiará y en cuánto. |
| **Idempotencia** | Repetir la misma confirmación con la misma clave devuelve la misma operación, nunca dos. |

## 2. Reglas de inventario (obligatorias)

1. `cantidad_base = cantidad_presentación × factor_base`, redondeada al paso mínimo de la unidad base.
2. Paso mínimo: **1 unidad**, **1 gramo**, **1 mililitro**. No se admite 0,5 unidades de un producto indivisible.
3. Un producto activo tiene **una sola** existencia por almacén. Las presentaciones no multiplican el stock.
4. Todo ingreso confirmed suma; toda venta confirmada resta; un reverso hace lo contrario. No existen otras salidas comerciales.
5. Las existencias nunca quedan negativas: si no hay stock, la operación se rechaza **completa** (nada parcial).
6. La valorización usa **costo promedio ponderado móvil** sobre la unidad base.
7. Cada detalle guarda *snapshots* (`factor_snapshot`, `precio_unitario`, `costo_base_snapshot`). Cambiar un dato maestro no altera el pasado.
8. El saldo siempre se puede explicar sumando los movimientos del kardex. La conciliación compara ambas fuentes y reporta diferencias **sin corregirlas** en silencio.
9. Un producto o proveedor inactivo no es seleccionable para nuevas operaciones, pero permanece visible en el histórico.
10. No se permite el borrado físico de datos con historial.

## 3. Historias de usuario

### Vender

- **HU-V01.** Como vendedor, quiero buscar un producto por nombre, código o código de barras y agregarlo al carrito con la cantidad y la presentación que el cliente pidió, para cobrar en pocos segundos.
  - Criterios: la búsqueda muestra nombre, presentación y stock; el foco permanece en el buscador tras añadir; el total se actualiza sin confirmar.
- **HU-V02.** Como vendedor, quiero ver el impacto exacto en el inventario antes de confirmar («−750 g»), para no prometer stock que no existe.
- **HU-V03.** Como vendedor, quiero que un doble clic no genere dos ventas, para no perder mercadería ni cobrar dos veces.
- **HU-V04.** Como vendedor, quiero que el sistema me avise con el saldo real si otra caja vendió antes lo que yo estaba por vender, para ajustar la cantidad y seguir vendiendo.

### Recibir

- **HU-R01.** Como administrador, quiero iniciar una recepción eligiendo el proveedor y ver sus productos habituales con el último costo, para registrar la mercadería sin reescribir datos.
- **HU-R02.** Como administrador, quiero ver el total y la conversión a unidad base antes de confirmar, para detectar errores de presentación o cantidad.
- **HU-R03.** Como administrador, quiero crear un producto nuevo durante la recepción sin perder las líneas ya escritas, para abastecer un artículo que aún no estaba en el catálogo.
- **HU-R04.** Como administrador, quiero que el costo registrado sea el real, aunque difiera del historial, para que el costo promedio refleje la realidad.

### Explorar

- **HU-E01.** Como responsable, quiero ver la existencia en unidades que entiendo (45,500 kg / 208 unidades) y no solo en gramos, para no tener que calcular mentalmente.
- **HU-E02.** Como responsable, quiero ver la huella del producto con tipo, cantidad, saldo y referencia, para entender por qué cambió el stock.
- **HU-E03.** Como responsable, quiero una lista ordenada por urgencia de reposición con el proveedor sugerido, para saber qué comprar antes.

### Administrar

- **HU-A01.** Como administrador, quiero anular una venta autorizada que quedó mal registrada, para restituir el stock sin borrar la evidencia.
- **HU-A02.** Como administrador, quiero registrar un ajuste por rotura o pérdida con motivo documentado, para que el inventario real y el registrado coincidan.
- **HU-A03.** Como administrador, quiero crear un respaldo verificable y saber restaurarlo, para no perder el negocio por una falla del equipo.

## 4. Casos de borde y comportamiento esperado

| Caso | Comportamiento esperado |
|---|---|
| Venta por debajo del stock disponible | Se rechaza con `409` indicando producto, solicitado y disponible. No se crea venta parcial. |
| Dos cajas de venta simultáneas sobre la última unidad | Una sola operación es válida; la otra recibe `409`. El stock nunca queda negativo. |
| Doble clic en «Confirmar venta» | La misma `idempotency_key` devuelve la misma venta; el stock se descuenta una vez. |
| Venta de 0,5 unidades de un producto indivisible | Se rechaza con `400` explicando que la presentación no admite fracciones. |
| Venta de 0,750 kg de un producto en gramos | Se registra −750 g exactos. |
| Cambio de precio después de vender | La venta histórica conserva su precio; el nuevo precio solo aplica a ventas futuras. |
| Cambio de factor de conversión después de comprar | El historial conserva el factor original. |
| Anulación de una venta ya anulada | Se rechaza (`400`); no se generan contramovimientos duplicados. |
| Anulación cuando parte de la mercadería ya se vendió | Se rechaza: no se puede devolver al stock lo que ya salió. |
| Producto desactivado con historial | No seleccionable para nuevas operaciones; su histórico permanece visible. |
| Código interno duplicado | Se rechaza con mensaje claro; se puede buscar por similitud para no duplicar. |
| Código de barras duplicado | Se rechaza con mensaje claro. |
| Ingreso con proveedor inactivo | Se rechaza: el proveedor debe estar activo. |
| Abastecimiento sin proveedor | No permitido: el proveedor es obligatorio. |
| Venta que deja el stock en cero | Se acepta; el producto pasa a estado «Agotado» en los filtros. |
| Ajuste que dejaría stock negativo | Se rechaza con `409` salvo autorización explícita de sobreventa (no habilitada en V1). |
| Importación de Excel con filas inválidas | Vista previa con el detalle de errores; las filas inválidas no se dan de alta. |
| Operación sin Internet | Funciona con normalidad: no hay dependencias externas en tiempo de ejecución. |
| Cliente sin permiso intenta anular | El servidor responde `403` aunque la interfaz muestre el botón. |

## 5. Supuestos de V1 (pendientes de confirmación con el negocio)

- Venta simple al precio de presentación, sin crédito ni descuentos complejos.
- Una sola ubicación física (un almacén) y un solo tipo de comprobante interno por operación.
- El precio de venta solo lo modifica el administrador.
- Los comprobantes de V1 son **internos** y no sustituyen los comprobantes tributarios exigibles.
- No se manejan lotes ni fechas de vencimiento en V1 (queda como punto de extensión).

### Decisiones ya tomadas en esta fase

| Decisión | Motivo |
|---|---|
| Unidad base obligatoria por producto | Evita inventarios duplicados por presentación (plan §6.1). |
| Paso mínimo 1 unidad / 1 g / 1 ml | Coherente con la regla de "no vender media unidad indivisible". |
| Costo promedio ponderado móvil | Valuation simple y auditable sobre la unidad base (plan §6.2). |
| Anulación por contramovimiento, nunca por borrado | Conserva la evidencia comercial (plan §4.4). |
| Idempotencia por clave en la confirmación de venta | Evita duplicados por doble clic o reintentos (plan §6.3). |
| Bloqueo de existencias con `SELECT ... FOR UPDATE` | Evita stock negativo con ventas concurrentes (plan §6.3). |
| Redondeo monetario a 2 decimales y costo unitario a 6 | Define la política de redondeo de forma explícita. |
