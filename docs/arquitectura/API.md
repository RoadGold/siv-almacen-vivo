# Contrato de API · SIV · Almacén Vivo

Base: `http://127.0.0.1:8000/api/v1` · Documentación interactiva: `http://127.0.0.1:8000/api/docs`

## Convenciones

- Todos los importes y cantidades viajan como **cadenas decimales** (`"48"`, `"0.75"`). Nunca `float`.
- Todas las respuestas de listado usan el sobre `Pagina`:
  `{ "items": [...], "total": 12, "pagina": 1, "tamano": 20, "paginas": 1 }`.
- Los errores usan el sobre:
  `{ "error": { "codigo": "stock_insuficiente", "mensaje": "...", "detalle": { ... } } }`
  con código HTTP `400` (regla de negocio), `403` (permiso), `404`, `409` (conflicto/stock), `422` (validación).
- Autenticación: `Authorization: Bearer <token>`.
- Las confirmaciones de venta aceptan `idempotency_key` (string, única) para evitar duplicados.

## Autenticación

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| POST | `/auth/login` | `{ "usuario": "admin", "password": "..." }` | `{ "access_token", "token_type", "expires_in", "usuario": {...} }` |
| GET | `/auth/me` | — | `{ "id", "nombre", "usuario", "activo", "roles": [...], "permisos": [...] }` |
| POST | `/auth/logout` | — | `{ "mensaje": "..." }` |

## Catálogo

| Método | Ruta | Notas |
|---|---|---|
| GET | `/catalogo/productos?q=&categoria_id=&marca_id=&activo=&pagina=&tamano=` | Búsqueda tolerante (sin acentos/mayúsculas) |
| GET | `/catalogo/productos/{id}` | Incluye `presentaciones[]` |
| POST | `/catalogo/productos` | `{ codigo, nombre, descripcion?, categoria_id?, marca_id?, unidad_base_id, stock_minimo_base, permite_fraccion, activo, presentaciones[] }` |
| PATCH | `/catalogo/productos/{id}` | Campos opcionales |
| POST | `/catalogo/productos/{id}/presentaciones` | `{ nombre, factor_base, precio_venta, costo_referencia?, codigo_barras?, es_compra, es_venta, permite_fraccion }` |
| PATCH | `/catalogo/presentaciones/{id}` | Permite cambiar precio/factor (el historial conserva snapshots) |
| DELETE | `/catalogo/presentaciones/{id}` | Desactiva (no borra) |
| GET/POST | `/catalogo/unidades`, `/catalogo/categorias`, `/catalogo/marcas` | Listados y altas |
| GET | `/catalogo/buscar?q=` | Buscador universal agrupado por tipo |
| GET | `/catalogo/importar/plantilla` | Plantilla Excel del catálogo (descarga, con hoja «Ayuda») |
| POST | `/catalogo/importar/previsualizar` | `multipart/form-data` con `archivo` → vista previa, sin escribir en la base |
| POST | `/catalogo/importar/confirmar` | `multipart/form-data` con `archivo` (+ `aplicar_stock_inicial`, `almacen_id`) → aplica las filas válidas |

**Columnas de la plantilla**: `Código`, `Nombre del producto`, `Categoría`, `Marca`,
`Unidad base (UND/GR/ML)`, `Stock mínimo`, `Presentación de venta`, `Factor de conversión`,
`Precio de venta`, `Costo de referencia`, `Código de barras`, `¿Admite fracción?`,
`Stock inicial`, `Costo unitario inicial`, `Código del proveedor`, `¿Proveedor habitual?`,
`Presentación de compra`.

**Reglas del importador**:

- El **stock inicial se aplica una sola vez por producto** y solo si el producto **no tiene
  existencias**; así, repetir la importación no duplica el stock.
- La vista previa distingue **errores** (la fila no se importa) de **avisos** (la fila se importa,
  pero conviene revisarla: stock repetido, producto con existencias, posible duplicado por nombre).
- El **proveedor es opcional**: si no se conoce, la celda queda vacía y el vínculo se crea más
  adelante. Si se indica un código que no existe, la fila **se importa igual** y queda un aviso
  («el vínculo no se creará»); el contador `vinculos_proveedor` solo cuenta los que sí se crean.

`presentaciones[]` devuelve: `{ id, producto_id, nombre, factor_base, precio_venta, costo_referencia, codigo_barras, es_compra, es_venta, permite_fraccion, activo }`.

## Proveedores

| Método | Ruta | Notas |
|---|---|---|
| GET | `/proveedores?q=&activo=&pagina=&tamano=` | Busca por razón social, código, RUC o contacto |
| GET | `/proveedores/{id}` | Ficha |
| POST | `/proveedores` | `{ codigo, razon_social, nombre_comercial?, ruc?, telefono?, contacto?, direccion?, email?, observaciones?, activo }` |
| PATCH | `/proveedores/{id}` | Campos opcionales |
| GET | `/proveedores/{id}/productos` | Productos habituales con presentación y último costo |
| GET | `/proveedores/{id}/historial` | Abastecimientos del proveedor |
| GET | `/proveedores/{id}/costos?producto_id=` | Histórico de costos |
| POST | `/proveedores/vinculos` | `{ producto_id, proveedor_id, habitual, presentacion_id?, observacion? }` |

## Abastecimientos

| Método | Ruta | Notas |
|---|---|---|
| POST | `/abastecimientos/previsualizar` | `{ proveedor_id, almacen_id?, fecha?, documento?, observaciones?, lineas[] }` → `{ total, lineas[], alertas_stock_minimo }` |
| POST | `/abastecimientos` | Confirma y mueve existencias. Respuesta `AbastecimientoOut` |
| GET | `/abastecimientos?proveedor_id=&desde=&hasta=&estado=&pagina=&tamano=` | Historial |
| GET | `/abastecimientos/{id}` | Detalle con líneas |
| POST | `/abastecimientos/{id}/anular` | `{ motivo }` — genera contramovimientos |

Línea de entrada/salida: `{ producto_id, presentacion_id, cantidad, costo_unitario }` (en venta, `precio_unitario` es opcional).

> **Precio:** el servidor siempre recalcula el precio. Si la venta incluye `precio_unitario`, solo se
> respeta cuando quien opera tiene el permiso `precios.gestionar` (administrador); en caso contrario
> se aplica el precio de la presentación.

`PrevisualizacionOut.lineas[]`: `{ producto_id, producto_codigo, producto_nombre, presentacion_id, presentacion_nombre, cantidad, factor_snapshot, cantidad_base, unidad_base, costo_unitario, subtotal, stock_actual_base, stock_resultante_base, alerta }`.

## Ventas

| Método | Ruta | Notas |
|---|---|---|
| POST | `/ventas/previsualizar` | `{ lineas[], almacen_id?, idempotency_key? }` → `{ total, costo_estimado, lineas[], alertas[] }` |
| POST | `/ventas` | Confirma y descuenta stock. Respuesta `VentaOut` |
| GET | `/ventas?desde=&hasta=&estado=&usuario_id=&pagina=&tamano=` | Historial |
| GET | `/ventas/{id}` | Detalle |
| POST | `/ventas/{id}/anular` | `{ motivo }` |

`PrevisualizacionVentaOut.lineas[]`: `{ producto_id, producto_codigo, producto_nombre, presentacion_id, presentacion_nombre, cantidad, factor_snapshot, cantidad_base, unidad_base, precio_unitario, subtotal, stock_actual_base, stock_resultante_base, costo_base, alerta }`.

`VentaOut`: `{ id, numero, almacen_id, fecha, estado, total, costo_total, cliente, observaciones, usuario, created_at, detalles[] }`.
`detalles[]`: `{ id, producto_id, presentacion_id, cantidad, factor_snapshot, cantidad_base, precio_unitario, subtotal, costo_total_linea, producto_codigo, producto_nombre, presentacion_nombre }`.

## Inventario

| Método | Ruta | Notas |
|---|---|---|
| GET | `/inventario/existencias?almacen_id=&q=&categoria_id=&estado=&pagina=&tamano=` | `estado` ∈ `agotado`, `bajo_minimo`, `disponible` |
| GET | `/inventario/productos/{id}/ficha` | Ficha viva: existencias, proveedores, huella reciente |
| GET | `/inventario/movimientos?producto_id=&almacen_id=&tipo=&desde=&hasta=&pagina=&tamano=` | Kardex (incluye `producto_codigo`, `producto_nombre` y `almacen`) |
| GET | `/inventario/radar-reposicion?almacen_id=&limite=` | Prioridad de reposición con proveedor sugerido |
| POST | `/inventario/ajustes` | `{ almacen_id, producto_id, cantidad_base, motivo }` (signo = suma o resta) |
| POST | `/inventario/inventario-inicial` | `{ almacen_id?, referencia?, lineas[] }` — carga inicial (no es una compra) |
| GET | `/inventario/conciliacion` | Diferencias kardex ↔ existencias (solo admin) |

`ExistenciaOut`: `{ producto_id, almacen_id, codigo, producto, categoria, unidad_base, cantidad_base, costo_promedio_base, valor_costo, stock_minimo_base, presentacion_principal, cantidad_presentacion, estado, ubicacion }`.

## Reportes

| Método | Ruta | Notas |
|---|---|---|
| GET | `/reportes/ventas?desde=&hasta=` | `{ periodo: {operaciones,total,costo,margen_bruto_estimado,por_dia[]}, por_producto[], por_categoria[], por_usuario[] }` |
| GET | `/reportes/abastecimientos?desde=&hasta=` | Abastecimientos por proveedor |
| GET | `/reportes/costos?producto_id=&proveedor_id=` | Histórico de costos de compra |
| GET | `/reportes/inventario?almacen_id=` | Inventario valorizado a costo promedio |
| GET | `/reportes/margen?desde=&hasta=` | Margen **bruto estimado** + nota de lectura |
| GET | `/reportes/ventas/exportar?desde=&hasta=` | Descarga CSV (UTF-8 con BOM) |

## Configuración e impresión

| Método | Ruta | Notas |
|---|---|---|
| GET | `/configuracion` | Valores y descripciones (datos del negocio, formato del ticket, límites de la caja) |
| PUT | `/configuracion` | Guarda la configuración (solo administrador) |
| GET | `/impresora/estado` | Activada/conectada, host, puerto, columnas, QR y corte |
| POST | `/impresora/prueba` | Imprime un ticket de prueba |
| GET | `/impresora/ticket/{venta_id}` | Vista en texto del ticket (sin imprimir) |
| POST | `/ventas/{id}/imprimir` | Imprime o reimprime el ticket de una venta |

**Precios variables en la caja**: la venta acepta `precio_unitario` y `motivo_precio` por línea. El
servidor lo revalida: si el descuento supera el límite configurado (`venta_descuento_maximo_porcentaje`)
y quien opera no tiene `precios.gestionar`, la venta se rechaza con `409 precio_fuera_de_limite`.
Cada cambio aplicado queda en la auditoría (`venta.precio_modificado`) y en el detalle
(`precio_original`, `motivo_precio`, `descuento_porcentaje`).

**Impresión**: la venta se registra **antes** de imprimir. Si la impresora falla, la venta se
conserva con `ticket_impreso = false` y `impresion_error`, y cada intento queda en la tabla
`impresiones_venta`. Los parámetros de la impresora (`IMPRESORA_HOST`, `IMPRESORA_PUERTO`,
`IMPRESORA_PAGINA_CODIGO`, `IMPRESORA_CORTAR`, `IMPRESORA_QR`) se leen del `.env`.

## Dashboard y administración
| Método | Ruta | Notas |
|---|---|---|
| GET | `/dashboard/resumen` | `{ fecha, ventas_dia, cantidad_ventas_dia, ingresos_dia, productos_agotados, productos_bajo_minimo, valor_inventario_costo, total_productos, ultimo_ingreso, ultima_venta }` |
| GET | `/admin/usuarios` | Listado paginado |
| POST | `/admin/usuarios` | `{ nombre, usuario, password, rol, activo }` |
| PATCH | `/admin/usuarios/{id}` | Actualización |
| GET | `/admin/auditoria` | Registro de acciones sensibles |
| GET | `/api/salud` | Estado del servidor (sin autenticación) |

## Permisos

`usuario.permisos` trae la lista completa; la interfaz oculta lo no permitido, pero **el servidor es la autoridad**: un `403` bloquea la acción aunque la interfaz la muestre.
