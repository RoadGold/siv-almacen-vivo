# Esquema de la base de datos · SIV · Almacén Vivo

> Documento generado automáticamente desde la base de datos viva con `python -m app.cli.esquema_base_datos`. Si cambia el esquema, vuelve a generarlo: así nunca queda viejo.

Versión del esquema (Alembic): `b8c4d2f71a35`.

## 1. Reglas del modelo

- **Todo el dinero y las cantidades son `NUMERIC`**, nunca `float`: los importes
  viajan como cadenas decimales y la aritmética es exacta (AD-02).
- **Nada se borra**: los productos, proveedores y categorías se desactivan
  (`activo = false`); las operaciones se anulan o se revierten con contramovimientos.
- **Los detalles guardan *snapshots*** (factor, precio y costo del momento): cambiar
  un precio o un factor hoy no altera las ventas de ayer (AD-09).
- **El lote es la fuente de verdad del inventario**: `existencias` es la caché
  consolidada, y `movimientos_inventario` es el historial (AD-15).
- **Las claves foráneas que borran** lo hacen con `SET NULL` o `CASCADE` para no
  perder la evidencia comercial (plan §6.5).
- **Los importes se redondean en el servidor**: 2 decimales para dinero, 4 para
  cantidades y 6 para costos unitarios.

## 2. Diagrama de relaciones

```mermaid
erDiagram
    usuarios {id PK}
    usuario_roles {usuario_id PK}
    usuario_roles {rol_id PK}
    roles {id PK}
    configuracion {clave PK}
    secuencias {tipo PK}
    secuencias {almacen_id PK}
    almacenes {id PK}
    unidades_medida {id PK}
    categorias {id PK}
    marcas {id PK}
    productos {id PK}
    presentaciones_producto {id PK}
    proveedores {id PK}
    productos_proveedores {id PK}
    lotes_inventario {id PK}
    lotes_precios {id PK}
    existencias {id PK}
    movimientos_inventario {id PK}
    ajustes_inventario {id PK}
    abastecimientos {id PK}
    detalle_abastecimientos {id PK}
    ventas {id PK}
    detalle_ventas {id PK}
    impresiones_venta {id PK}
    auditoria {id PK}
    usuario_roles ||--o{ roles : "ROL_ID"
    usuario_roles ||--o{ usuarios : "USUARIO_ID"
    secuencias ||--o{ almacenes : "ALMACEN_ID"
    productos ||--o{ categorias : "CATEGORIA_ID"
    productos ||--o{ marcas : "MARCA_ID"
    productos ||--o{ unidades_medida : "UNIDAD_BASE_ID"
    presentaciones_producto ||--o{ productos : "PRODUCTO_ID"
    productos_proveedores ||--o{ presentaciones_producto : "PRESENTACION_ID"
    productos_proveedores ||--o{ productos : "PRODUCTO_ID"
    productos_proveedores ||--o{ proveedores : "PROVEEDOR_ID"
    lotes_inventario ||--o{ proveedores : "PROVEEDOR_ID"
    lotes_inventario ||--o{ abastecimientos : "ABASTECIMIENTO_ID"
    lotes_inventario ||--o{ almacenes : "ALMACEN_ID"
    lotes_inventario ||--o{ detalle_abastecimientos : "DETALLE_ABASTECIMIENTO_ID"
    lotes_inventario ||--o{ presentaciones_producto : "PRESENTACION_PRINCIPAL_ID"
    lotes_inventario ||--o{ productos : "PRODUCTO_ID"
    lotes_inventario ||--o{ usuarios : "USUARIO_ID"
    lotes_precios ||--o{ lotes_inventario : "LOTE_ID"
    lotes_precios ||--o{ presentaciones_producto : "PRESENTACION_ID"
    existencias ||--o{ almacenes : "ALMACEN_ID"
    existencias ||--o{ productos : "PRODUCTO_ID"
    movimientos_inventario ||--o{ almacenes : "ALMACEN_ID"
    movimientos_inventario ||--o{ productos : "PRODUCTO_ID"
    movimientos_inventario ||--o{ usuarios : "USUARIO_ID"
    movimientos_inventario ||--o{ lotes_inventario : "LOTE_ID"
    ajustes_inventario ||--o{ almacenes : "ALMACEN_ID"
    ajustes_inventario ||--o{ productos : "PRODUCTO_ID"
    ajustes_inventario ||--o{ usuarios : "USUARIO_ID"
    ajustes_inventario ||--o{ lotes_inventario : "LOTE_ID"
    abastecimientos ||--o{ almacenes : "ALMACEN_ID"
    abastecimientos ||--o{ usuarios : "ANULADO_POR_ID"
    abastecimientos ||--o{ proveedores : "PROVEEDOR_ID"
    abastecimientos ||--o{ usuarios : "USUARIO_ID"
    detalle_abastecimientos ||--o{ abastecimientos : "ABASTECIMIENTO_ID"
    detalle_abastecimientos ||--o{ presentaciones_producto : "PRESENTACION_ID"
    detalle_abastecimientos ||--o{ productos : "PRODUCTO_ID"
    detalle_abastecimientos ||--o{ lotes_inventario : "LOTE_ID"
    ventas ||--o{ almacenes : "ALMACEN_ID"
    ventas ||--o{ usuarios : "ANULADO_POR_ID"
    ventas ||--o{ usuarios : "USUARIO_ID"
    detalle_ventas ||--o{ presentaciones_producto : "PRESENTACION_ID"
    detalle_ventas ||--o{ productos : "PRODUCTO_ID"
    detalle_ventas ||--o{ ventas : "VENTA_ID"
    detalle_ventas ||--o{ lotes_inventario : "LOTE_ID"
    impresiones_venta ||--o{ usuarios : "USUARIO_ID"
    impresiones_venta ||--o{ ventas : "VENTA_ID"
    auditoria ||--o{ usuarios : "ACTOR_ID"
```

## 3. Tablas

### Seguridad, roles y configuración

### `usuarios`

Cuentas de acceso al sistema. La contraseña nunca se guarda en claro: se guarda su hash (Argon2id).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('usuarios_id_seq'::regclass)` |
| `nombre` | varchar(120) | no |  | — |
| `usuario` | varchar(60) | no | única | — |
| `password_hash` | varchar(255) | no |  | — |
| `activo` | boolean | no |  | — |
| `ultimo_acceso` | timestamptz | sí |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **2**.

Índices: `pk_usuarios`, `uq_usuarios_usuario`.

### `usuario_roles`

Qué roles tiene cada usuario (un usuario puede tener varios).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `usuario_id` | integer | no | PK | — |
| `rol_id` | integer | no | PK | — |

Filas ahora mismo: **2**.

Índices: `pk_usuario_roles`.

### `roles`

Los roles del sistema: `administrador` y `vendedor`. Los permisos se declaran aquí (AD-10).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('roles_id_seq'::regclass)` |
| `nombre` | varchar(50) | no | única | — |
| `descripcion` | varchar(200) | sí |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **2**.

Índices: `pk_roles`, `uq_roles_nombre`.

### `configuracion`

Clave/valor con los datos del negocio (nombre, RUC) y las reglas de la caja (descuento máximo, formato del ticket).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `clave` | varchar(80) | no | PK | — |
| `valor` | text | sí |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `pk_configuracion`.

### `secuencias`

Correlativos de comprobantes por almacén: `V-000001`, `A-000001`, `AJ-000001`.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `tipo` | varchar(20) | no | PK | — |
| `almacen_id` | integer | no | PK | — |
| `valor` | integer | no |  | — |

Filas ahora mismo: **0**.

Índices: `pk_secuencias`.

### Almacén y catálogo

### `almacenes`

Almacenes del negocio. El primero activo es el principal.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('almacenes_id_seq'::regclass)` |
| `nombre` | varchar(120) | no |  | — |
| `activo` | boolean | no |  | — |
| `es_principal` | boolean | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **1**.

Índices: `pk_almacenes`.

### `unidades_medida`

Unidades base: `UND` (unidad), `GR` (gramo), `ML` (mililitro). El paso mínimo define la fracción mínima.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('unidades_medida_id_seq'::regclass)` |
| `codigo` | varchar(20) | no | única | — |
| `nombre` | varchar(60) | no |  | — |
| `dimension` | varchar(20) | no |  | — |
| `paso_minimo` | integer | no |  | — |
| `activo` | boolean | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **5**.

Índices: `pk_unidades_medida`, `uq_unidades_medida_codigo`.

### `categorias`

Categorías de los productos (balanceados, mascotas, primario, medicamentos…).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('categorias_id_seq'::regclass)` |
| `nombre` | varchar(120) | no |  | — |
| `activo` | boolean | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `pk_categorias`.

### `marcas`

Marcas de los productos (Vitamaxpro, Invita, Tomasino, Sequeiros…).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('marcas_id_seq'::regclass)` |
| `nombre` | varchar(120) | no |  | — |
| `activo` | boolean | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `pk_marcas`.

### `productos`

Maestro de productos. `nombre_normalizado` es el nombre sin acentos ni mayúsculas, para las búsquedas tolerantes.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('productos_id_seq'::regclass)` |
| `codigo` | varchar(40) | no | única | — |
| `nombre` | varchar(200) | no |  | — |
| `nombre_normalizado` | varchar(200) | no |  | — |
| `descripcion` | text | sí |  | — |
| `categoria_id` | integer | sí | FK → `categorias.id` (no action) | — |
| `marca_id` | integer | sí | FK → `marcas.id` (no action) | — |
| `unidad_base_id` | integer | no | FK → `unidades_medida.id` (no action) | — |
| `stock_minimo_base` | numeric(20,4) | no |  | — |
| `permite_fraccion` | boolean | no |  | — |
| `activo` | boolean | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_productos_nombre_normalizado`, `pk_productos`, `uq_productos_codigo`.

### `presentaciones_producto`

Los empaques de cada producto (saco 40 kg, caja x24, bolsa 1 kg). `factor_base` convierte a la unidad base.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('presentaciones_producto_id_seq'::regclass)` |
| `producto_id` | integer | no | única | — |
| `nombre` | varchar(80) | no | única | — |
| `factor_base` | numeric(20,6) | no |  | — |
| `precio_venta` | numeric(14,2) | no |  | — |
| `costo_referencia` | numeric(14,2) | no |  | — |
| `codigo_barras` | varchar(64) | sí |  | — |
| `es_compra` | boolean | no |  | — |
| `es_venta` | boolean | no |  | — |
| `permite_fraccion` | boolean | no |  | — |
| `activo` | boolean | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_presentaciones_producto_codigo_barras`, `ix_presentaciones_producto_producto_id`, `pk_presentaciones_producto`, `uq_pp_producto_nombre`.

### `proveedores`

Los proveedores (distribuidores).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('proveedores_id_seq'::regclass)` |
| `codigo` | varchar(40) | no | única | — |
| `razon_social` | varchar(200) | no |  | — |
| `nombre_comercial` | varchar(200) | sí |  | — |
| `ruc` | varchar(20) | sí |  | — |
| `telefono` | varchar(40) | sí |  | — |
| `contacto` | varchar(120) | sí |  | — |
| `direccion` | varchar(240) | sí |  | — |
| `email` | varchar(120) | sí |  | — |
| `observaciones` | text | sí |  | — |
| `activo` | boolean | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_proveedores_ruc`, `pk_proveedores`, `uq_proveedores_codigo`.

### `productos_proveedores`

Vínculo N:M entre productos y proveedores, con su presentación habitual y el último costo.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('productos_proveedores_id_seq'::regclass)` |
| `producto_id` | integer | no | única | — |
| `proveedor_id` | integer | no | única | — |
| `habitual` | boolean | no |  | — |
| `presentacion_id` | integer | sí | FK → `presentaciones_producto.id` (no action) | — |
| `ultimo_costo` | numeric(14,2) | sí |  | — |
| `ultima_fecha_compra` | date | sí |  | — |
| `observacion` | text | sí |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_productos_proveedores_producto_id`, `ix_productos_proveedores_proveedor_id`, `pk_productos_proveedores`, `uq_pp_proveedor_producto`.

### Inventario por lotes

### `lotes_inventario`

Cada línea de ingreso crea un lote: su stock, su costo y su precio de venta propios. Es la fuente de verdad del inventario.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('lotes_inventario_id_seq'::regclass)` |
| `producto_id` | integer | no | FK → `productos.id` (cascade) | — |
| `codigo_lote` | varchar(60) | no | única | — |
| `fecha_ingreso` | date | sí |  | — |
| `cantidad_inicial` | numeric(20,4) | no |  | — |
| `cantidad_disponible` | numeric(20,4) | no |  | — |
| `costo_base` | numeric(16,6) | no |  | — |
| `costo_unitario` | numeric(14,2) | no |  | — |
| `precio_venta` | numeric(14,2) | no |  | — |
| `presentacion_principal_id` | integer | sí | FK → `presentaciones_producto.id` (set null) | — |
| `almacen_id` | integer | no | FK → `almacenes.id` (no action) | — |
| `abastecimiento_id` | integer | sí | FK → `abastecimientos.id` (set null) | — |
| `detalle_abastecimiento_id` | integer | sí | FK → `detalle_abastecimientos.id` (set null) | — |
| `estado` | varchar(20) | no |  | — |
| `origen` | varchar(20) | no |  | — |
| `usuario_id` | integer | sí | FK → `usuarios.id` (no action) | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |
| `costo_transporte` | numeric(14,2) | no |  | `'0'::numeric` |
| `proveedor_id` | integer | sí | FK → `proveedores.id` (set null) | — |

Filas ahora mismo: **0**.

Índices: `ix_lotes_inventario_abastecimiento_id`, `ix_lotes_inventario_almacen_id`, `ix_lotes_inventario_estado`, `ix_lotes_inventario_fecha_ingreso`, `ix_lotes_inventario_producto_id`, `ix_lotes_inventario_proveedor_id`, `pk_lotes_inventario`, `uq_lotes_inventario_codigo_lote`.

### `lotes_precios`

Precio de venta de una presentación dentro de un lote (un mismo lote se puede vender en sacos o por kilos).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('lotes_precios_id_seq'::regclass)` |
| `lote_id` | integer | no | única | — |
| `presentacion_id` | integer | no | única | — |
| `precio` | numeric(14,2) | no |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_lotes_precios_lote_id`, `ix_lotes_precios_presentacion_id`, `pk_lotes_precios`, `uq_lotes_precios_lote_presentacion`.

### `existencias`

Stock consolidado por (almacén, producto). Es la lectura rápida; su valor se recalcula desde los lotes.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('existencias_id_seq'::regclass)` |
| `almacen_id` | integer | no | única | — |
| `producto_id` | integer | no | única | — |
| `cantidad_base` | numeric(20,4) | no |  | — |
| `costo_promedio_base` | numeric(16,6) | no |  | — |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_existencias_almacen_id`, `ix_existencias_producto_id`, `pk_existencias`, `uq_existencias_almacen_producto`.

### `movimientos_inventario`

El kardex: cada entrada, salida, reverso y ajuste con su saldo. Nunca se borra.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('movimientos_inventario_id_seq'::regclass)` |
| `producto_id` | integer | no | FK → `productos.id` (no action) | — |
| `almacen_id` | integer | no | FK → `almacenes.id` (no action) | — |
| `tipo` | varchar(30) | no |  | — |
| `cantidad_base_signed` | numeric(20,4) | no |  | — |
| `saldo_base_despues` | numeric(20,4) | no |  | — |
| `costo_unitario_base` | numeric(16,6) | no |  | — |
| `origen_tipo` | varchar(30) | no |  | — |
| `origen_id` | integer | no |  | — |
| `referencia` | varchar(40) | sí |  | — |
| `usuario_id` | integer | sí | FK → `usuarios.id` (no action) | — |
| `created_at` | timestamptz | no |  | `now()` |
| `lote_id` | integer | sí | FK → `lotes_inventario.id` (set null) | — |

Filas ahora mismo: **0**.

Índices: `ix_movimientos_inventario_almacen_id`, `ix_movimientos_inventario_created_at`, `ix_movimientos_inventario_lote_id`, `ix_movimientos_inventario_producto_id`, `ix_movimientos_inventario_tipo`, `pk_movimientos_inventario`.

### `ajustes_inventario`

Ajustes administrativos (pérdida, rotura, conteo) con su motivo.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('ajustes_inventario_id_seq'::regclass)` |
| `numero` | varchar(30) | no | única | — |
| `almacen_id` | integer | no | FK → `almacenes.id` (no action) | — |
| `producto_id` | integer | no | FK → `productos.id` (no action) | — |
| `tipo` | varchar(30) | no |  | — |
| `cantidad_base` | numeric(20,4) | no |  | — |
| `motivo` | text | no |  | — |
| `estado` | varchar(20) | no |  | — |
| `usuario_id` | integer | no | FK → `usuarios.id` (no action) | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |
| `lote_id` | integer | sí | FK → `lotes_inventario.id` (set null) | — |

Filas ahora mismo: **0**.

Índices: `ix_ajustes_inventario_lote_id`, `ix_ajustes_inventario_producto_id`, `pk_ajustes_inventario`, `uq_ajustes_inventario_numero`.

### Operaciones comerciales

### `abastecimientos`

Cabecera de los ingresos de mercadería. Siempre tienen proveedor.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('abastecimientos_id_seq'::regclass)` |
| `numero` | varchar(30) | no | única | — |
| `proveedor_id` | integer | no | FK → `proveedores.id` (no action) | — |
| `almacen_id` | integer | no | FK → `almacenes.id` (no action) | — |
| `fecha` | date | no |  | — |
| `documento` | varchar(60) | sí |  | — |
| `observaciones` | text | sí |  | — |
| `estado` | varchar(20) | no |  | — |
| `usuario_id` | integer | no | FK → `usuarios.id` (no action) | — |
| `total` | numeric(14,2) | no |  | — |
| `anulado_por_id` | integer | sí | FK → `usuarios.id` (no action) | — |
| `anulado_at` | timestamptz | sí |  | — |
| `motivo_anulacion` | text | sí |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_abastecimientos_almacen_id`, `ix_abastecimientos_documento`, `ix_abastecimientos_estado`, `ix_abastecimientos_fecha`, `ix_abastecimientos_proveedor_id`, `pk_abastecimientos`, `uq_abastecimientos_numero`.

### `detalle_abastecimientos`

Líneas del ingreso, con el *snapshot* del factor y el costo, y el lote que generaron.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('detalle_abastecimientos_id_seq'::regclass)` |
| `abastecimiento_id` | integer | no | FK → `abastecimientos.id` (cascade) | — |
| `producto_id` | integer | no | FK → `productos.id` (no action) | — |
| `presentacion_id` | integer | no | FK → `presentaciones_producto.id` (no action) | — |
| `cantidad` | numeric(20,4) | no |  | — |
| `factor_snapshot` | numeric(20,6) | no |  | — |
| `cantidad_base` | numeric(20,4) | no |  | — |
| `costo_unitario` | numeric(14,2) | no |  | — |
| `costo_base` | numeric(16,6) | no |  | — |
| `subtotal` | numeric(14,2) | no |  | — |
| `lote_id` | integer | sí | FK → `lotes_inventario.id` (set null) | — |
| `costo_transporte` | numeric(14,2) | no |  | `'0'::numeric` |

Filas ahora mismo: **0**.

Índices: `ix_detalle_abastecimientos_abastecimiento_id`, `ix_detalle_abastecimientos_lote_id`, `ix_detalle_abastecimientos_producto_id`, `pk_detalle_abastecimientos`.

### `ventas`

Cabecera de las ventas: total, costo, forma de pago, vuelto y deuda.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('ventas_id_seq'::regclass)` |
| `numero` | varchar(30) | no | única | — |
| `almacen_id` | integer | no | FK → `almacenes.id` (no action) | — |
| `fecha` | date | no |  | — |
| `estado` | varchar(20) | no |  | — |
| `usuario_id` | integer | no | FK → `usuarios.id` (no action) | — |
| `total` | numeric(14,2) | no |  | — |
| `costo_total` | numeric(14,2) | no |  | — |
| `idempotency_key` | varchar(80) | sí | única | — |
| `cliente` | varchar(160) | sí |  | — |
| `observaciones` | text | sí |  | — |
| `anulado_por_id` | integer | sí | FK → `usuarios.id` (no action) | — |
| `anulado_at` | timestamptz | sí |  | — |
| `motivo_anulacion` | text | sí |  | — |
| `created_at` | timestamptz | no |  | `now()` |
| `updated_at` | timestamptz | no |  | `now()` |
| `ticket_impreso` | boolean | no |  | — |
| `impreso_at` | timestamptz | sí |  | — |
| `impresion_error` | text | sí |  | — |
| `forma_pago` | varchar(30) | sí |  | — |
| `monto_recibido` | numeric(14,2) | sí |  | — |
| `vuelto` | numeric(14,2) | sí |  | — |
| `deuda` | numeric(14,2) | sí |  | — |

Filas ahora mismo: **0**.

Índices: `ix_ventas_almacen_id`, `ix_ventas_estado`, `ix_ventas_fecha`, `pk_ventas`, `uq_ventas_idempotency_key`, `uq_ventas_numero`.

### `detalle_ventas`

Líneas de la venta, con el *snapshot* del precio y del costo, y el lote del que salió la mercadería.

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('detalle_ventas_id_seq'::regclass)` |
| `venta_id` | integer | no | FK → `ventas.id` (cascade) | — |
| `producto_id` | integer | no | FK → `productos.id` (no action) | — |
| `presentacion_id` | integer | no | FK → `presentaciones_producto.id` (no action) | — |
| `cantidad` | numeric(20,4) | no |  | — |
| `factor_snapshot` | numeric(20,6) | no |  | — |
| `cantidad_base` | numeric(20,4) | no |  | — |
| `precio_unitario` | numeric(14,2) | no |  | — |
| `costo_base_snapshot` | numeric(16,6) | no |  | — |
| `subtotal` | numeric(14,2) | no |  | — |
| `costo_total_linea` | numeric(14,2) | no |  | — |
| `precio_original` | numeric(14,2) | sí |  | — |
| `motivo_precio` | varchar(120) | sí |  | — |
| `lote_id` | integer | sí | FK → `lotes_inventario.id` (set null) | — |

Filas ahora mismo: **0**.

Índices: `ix_detalle_ventas_lote_id`, `ix_detalle_ventas_producto_id`, `ix_detalle_ventas_venta_id`, `pk_detalle_ventas`.

### `impresiones_venta`

Cada impresión del ticket, con su resultado (para reimprimir y auditar).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('impresiones_venta_id_seq'::regclass)` |
| `venta_id` | integer | no | FK → `ventas.id` (cascade) | — |
| `fecha` | timestamptz | no |  | `now()` |
| `resultado` | varchar(20) | no |  | — |
| `mensaje` | text | sí |  | — |
| `reimpresion` | boolean | no |  | — |
| `usuario_id` | integer | sí | FK → `usuarios.id` (no action) | — |
| `duracion_ms` | integer | sí |  | — |

Filas ahora mismo: **0**.

Índices: `ix_impresiones_venta_fecha`, `ix_impresiones_venta_venta_id`, `pk_impresiones_venta`.

### Auditoría

### `auditoria`

Bitácora de las acciones sensibles (cambios de precio, anulaciones, ajustes).

| Columna | Tipo | Nulo | Clave | Valor por defecto |
|---|---|:---:|---|---|
| `id` | integer | no | PK | `nextval('auditoria_id_seq'::regclass)` |
| `actor_id` | integer | sí | FK → `usuarios.id` (no action) | — |
| `accion` | varchar(60) | no |  | — |
| `entidad` | varchar(60) | no |  | — |
| `entidad_id` | integer | sí |  | — |
| `detalle` | text | sí |  | — |
| `created_at` | timestamptz | no |  | `now()` |

Filas ahora mismo: **0**.

Índices: `ix_auditoria_accion`, `ix_auditoria_created_at`, `ix_auditoria_entidad`, `pk_auditoria`.

## 4. Base limpia: lista de comprobación

Una base **limpia** (la de una instalación recién hecha) tiene:

| Tabla | Estado esperado |
|---|---|
| `productos` | 0 filas |
| `presentaciones_producto` | 0 filas |
| `proveedores` | 0 filas |
| `marcas` | 0 filas |
| `categorias` | 0 filas |
| `lotes_inventario` | 0 filas |
| `existencias` | 0 filas |
| `movimientos_inventario` | 0 filas |
| `ventas` | 0 filas |
| `abastecimientos` | 0 filas |
| `ajustes_inventario` | 0 filas |
| `impresiones_venta` | 0 filas |
| `auditoria` | 0 filas |
| `usuarios` | las que tenga (no se borran) |
| `almacenes` | las que tenga (no se borran) |
| `unidades_medida` | las que tenga (no se borran) |

Y las secuencias en cero, para que la primera venta sea `V-000001`.

Comprobaciones:

```powershell
# Ver el estado desde el sistema
#   Administrar -> Diagnóstico -> «Estado de la base de datos»

# Ver el estado desde la consola
cd backend
.\.venv\Scripts\python.exe -m app.cli.reiniciar_base --simular
```

## 5. Cómo dejar la base en este estado

```powershell
cd backend

# Vaciar la operación y conservar el catálogo
.\.venv\Scripts\python.exe -m app.cli.limpiar_operacion --simular
.\.venv\Scripts\python.exe -m app.cli.limpiar_operacion

# Dejar la base totalmente vacía (sin catálogo ni stock)
.\.venv\Scripts\python.exe -m app.cli.reiniciar_base --simular
.\.venv\Scripts\python.exe -m app.cli.reiniciar_base

# Volver a llenarla
.\.venv\Scripts\python.exe -m app.cli.datos_balanceados_cargar
.\.venv\Scripts\python.exe -m app.cli.cargar_inventario_tienda
```

