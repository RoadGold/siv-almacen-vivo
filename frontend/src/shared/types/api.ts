/**
 * Tipos del API de SIV · Almacén Vivo.
 * Reflejan los esquemas de `backend/app/schemas`.
 * Los importes y cantidades viajan como cadenas decimales.
 */

export interface Pagina<T> {
  items: T[];
  total: number;
  pagina: number;
  tamano: number;
  paginas: number;
}

export interface Usuario {
  id: number;
  nombre: string;
  usuario: string;
  activo: boolean;
  roles: string[];
  permisos: string[];
  ultimo_acceso?: string | null;
}

export interface RespuestaLogin {
  access_token: string;
  token_type: string;
  expires_in: number;
  usuario: Usuario;
}

export interface Presentacion {
  id: number;
  producto_id?: number | null;
  nombre: string;
  factor_base: string;
  precio_venta: string;
  costo_referencia?: string;
  codigo_barras?: string | null;
  es_compra: boolean;
  es_venta: boolean;
  permite_fraccion: boolean;
  activo: boolean;
}

/** Presentación tal como se envía al backend al crear o editar un producto. */
export interface PresentacionIn {
  nombre: string;
  factor_base: string;
  precio_venta: string;
  costo_referencia?: string;
  codigo_barras?: string | null;
  es_compra: boolean;
  es_venta: boolean;
  permite_fraccion: boolean;
}

export interface Producto {
  id: number;
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  categoria_id?: number | null;
  categoria?: string | null;
  marca_id?: number | null;
  marca?: string | null;
  unidad_base_id: number;
  unidad_base?: string | null;
  stock_minimo_base: string;
  permite_fraccion: boolean;
  activo: boolean;
  created_at?: string | null;
  presentaciones: Presentacion[];
}

export interface ExistenciaResumen {
  almacen_id: number;
  almacen?: string | null;
  cantidad_base: string;
  costo_promedio_base: string;
  presentacion_principal?: string | null;
  cantidad_presentacion?: string | null;
  unidad_base?: string | null;
}

export interface ProveedorProductoResumen {
  proveedor_id: number;
  proveedor: string;
  habitual: boolean;
  ultimo_costo?: string | null;
  ultima_fecha_compra?: string | null;
}

export interface MovimientoResumen {
  id: number;
  producto_codigo?: string | null;
  producto_nombre?: string | null;
  almacen?: string | null;
  tipo: string;
  cantidad_base_signed: string;
  saldo_base_despues: string;
  referencia?: string | null;
  origen_tipo?: string | null;
  origen_id?: number | null;
  usuario?: string | null;
  created_at?: string | null;
}

export interface ProductoFicha extends Producto {
  existencias: ExistenciaResumen[];
  proveedores: ProveedorProductoResumen[];
  ultimo_costo?: string | null;
  movimientos_recientes: MovimientoResumen[];
}

export interface UnidadMedida {
  id: number;
  codigo: string;
  nombre: string;
  dimension: string;
  paso_minimo: number;
  activo: boolean;
}

export interface Categoria {
  id: number;
  nombre: string;
  activo: boolean;
}

export interface Marca {
  id: number;
  nombre: string;
  activo: boolean;
}

export interface Proveedor {
  id: number;
  codigo: string;
  razon_social: string;
  nombre_comercial?: string | null;
  ruc?: string | null;
  telefono?: string | null;
  contacto?: string | null;
  direccion?: string | null;
  email?: string | null;
  observaciones?: string | null;
  activo: boolean;
}

export interface ProductoDelProveedor {
  id: number;
  producto_id: number;
  proveedor_id: number;
  codigo: string;
  nombre: string;
  unidad_base?: string | null;
  activo: boolean;
  presentacion_id?: number | null;
  presentacion_nombre?: string | null;
  factor_base?: string | null;
  ultimo_costo?: string | null;
  ultima_fecha_compra?: string | null;
  habitual: boolean;
  observacion?: string | null;
}

export interface VinculoProductoProveedor {
  id: number;
  producto_id: number;
  proveedor_id: number;
  habitual: boolean;
  presentacion_id?: number | null;
  ultimo_costo?: string | null;
  ultima_fecha_compra?: string | null;
  observacion?: string | null;
}

export interface Existencia {
  producto_id: number;
  almacen_id: number;
  codigo?: string | null;
  producto?: string | null;
  categoria?: string | null;
  unidad_base?: string | null;
  cantidad_base: string;
  costo_promedio_base: string;
  valor_costo: string;
  stock_minimo_base: string;
  presentacion_principal?: string | null;
  cantidad_presentacion?: string | null;
  estado: string;
  ubicacion?: string | null;
}

export interface Movimiento {
  id: number;
  producto_id: number;
  producto_codigo?: string | null;
  producto_nombre?: string | null;
  almacen_id: number;
  almacen?: string | null;
  tipo: string;
  cantidad_base_signed: string;
  saldo_base_despues: string;
  costo_unitario_base: string;
  origen_tipo?: string | null;
  origen_id?: number | null;
  referencia?: string | null;
  usuario?: string | null;
  created_at?: string | null;
}

export interface RadarReposicion {
  producto_id: number;
  codigo: string;
  producto: string;
  unidad_base?: string | null;
  cantidad_base: string;
  stock_minimo_base: string;
  cantidad_presentacion?: string | null;
  presentacion_principal?: string | null;
  proveedor_sugerido?: string | null;
  proveedor_id?: number | null;
  ultimo_costo?: string | null;
  prioridad: number;
  estado: string;
}

export interface ResumenDashboard {
  fecha: string;
  ventas_dia: string;
  cantidad_ventas_dia: number;
  ingresos_dia: string;
  productos_agotados: number;
  productos_bajo_minimo: number;
  valor_inventario_costo: string;
  total_productos: number;
  ultimo_ingreso?: string | null;
  ultima_venta?: string | null;
}

export interface LineaVentaIn {
  producto_id: number;
  presentacion_id: number;
  cantidad: string;
  precio_unitario?: string | null;
  precio_total?: string | null;
  motivo_precio?: string | null;
}

export interface VentaIn {
  almacen_id?: number | null;
  fecha?: string | null;
  cliente?: string | null;
  forma_pago?: string | null;
  monto_recibido?: string | null;
  observaciones?: string | null;
  idempotency_key?: string | null;
  lineas: LineaVentaIn[];
}

export interface LineaCalculadaVenta {
  producto_id: number;
  producto_codigo: string;
  producto_nombre: string;
  presentacion_id: number;
  presentacion_nombre: string;
  cantidad: string;
  factor_snapshot: string;
  cantidad_base: string;
  unidad_base?: string | null;
  precio_unitario: string;
  precio_original: string;
  precio_total: string;
  precio_total_original: string;
  descuento_porcentaje: string;
  descuento_monto: string;
  precio_permitido: boolean;
  motivo_precio?: string | null;
  subtotal: string;
  stock_actual_base: string;
  stock_resultante_base: string;
  costo_base?: string | null;
  alerta?: string | null;
}

export interface PrevisualizacionVenta {
  total: string;
  costo_estimado: string;
  lineas: LineaCalculadaVenta[];
  alertas: string[];
}

export interface DetalleVenta {
  id: number;
  producto_id: number;
  presentacion_id: number;
  cantidad: string;
  factor_snapshot: string;
  cantidad_base: string;
  precio_unitario: string;
  precio_original: string;
  motivo_precio?: string | null;
  descuento_porcentaje: string;
  subtotal: string;
  costo_total_linea: string;
  producto_codigo?: string | null;
  producto_nombre?: string | null;
  presentacion_nombre?: string | null;
}

export interface Venta {
  id: number;
  numero: string;
  almacen_id: number;
  fecha: string;
  estado: string;
  total: string;
  costo_total: string;
  cliente?: string | null;
  forma_pago?: string | null;
  monto_recibido?: string | null;
  vuelto?: string | null;
  observaciones?: string | null;
  usuario?: string | null;
  ticket_impreso: boolean;
  impreso_at?: string | null;
  impresion_error?: string | null;
  created_at?: string | null;
  detalles: DetalleVenta[];
}

export interface LineaAbastecimientoIn {
  producto_id: number;
  presentacion_id: number;
  cantidad: string;
  costo_unitario: string;
}

export interface AbastecimientoIn {
  proveedor_id: number;
  almacen_id?: number | null;
  fecha?: string | null;
  documento?: string | null;
  observaciones?: string | null;
  lineas: LineaAbastecimientoIn[];
}

export interface LineaCalculadaAbastecimiento {
  producto_id: number;
  producto_codigo: string;
  producto_nombre: string;
  presentacion_id: number;
  presentacion_nombre: string;
  cantidad: string;
  factor_snapshot: string;
  cantidad_base: string;
  unidad_base?: string | null;
  costo_unitario: string;
  subtotal: string;
  stock_actual_base: string;
  stock_resultante_base: string;
  alerta?: string | null;
}

export interface PrevisualizacionAbastecimiento {
  total: string;
  lineas: LineaCalculadaAbastecimiento[];
  alertas_stock_minimo: number;
}

export interface DetalleAbastecimiento {
  id: number;
  producto_id: number;
  presentacion_id: number;
  cantidad: string;
  factor_snapshot: string;
  cantidad_base: string;
  costo_unitario: string;
  subtotal: string;
  producto_codigo?: string | null;
  producto_nombre?: string | null;
  presentacion_nombre?: string | null;
}

export interface Abastecimiento {
  id: number;
  numero: string;
  proveedor_id: number;
  proveedor_nombre?: string | null;
  almacen_id: number;
  fecha: string;
  documento?: string | null;
  observaciones?: string | null;
  estado: string;
  total: string;
  usuario?: string | null;
  created_at?: string | null;
  detalles: DetalleAbastecimiento[];
}

export interface EstadoServidor {
  estado: string;
  servicio: string;
  version: string;
  entorno: string;
  moneda: string;
}

/* --- Reportes ------------------------------------------------------- */

export interface PeriodoVentas {
  desde: string;
  hasta: string;
  operaciones: number;
  total: string;
  costo: string;
  margen_bruto_estimado: string;
  por_dia: VentasPorDia[];
}

export interface VentasPorDia {
  fecha: string;
  operaciones: number;
  total: string;
  costo: string;
  margen_bruto_estimado: string;
}

export interface VentasPorProducto {
  producto_id: number;
  codigo: string;
  producto: string;
  cantidad_base: string;
  total: string;
  costo: string;
  margen_bruto_estimado: string;
}

export interface VentasPorCategoria {
  categoria: string;
  operaciones: number;
  total: string;
  costo: string;
  margen_bruto_estimado: string;
}

export interface VentasPorUsuario {
  usuario: string;
  operaciones: number;
  total: string;
}

export interface ReporteVentas {
  periodo: PeriodoVentas;
  por_producto: VentasPorProducto[];
  por_categoria: VentasPorCategoria[];
  por_usuario: VentasPorUsuario[];
}

export interface AbastecimientosPorProveedor {
  proveedor_id: number;
  proveedor: string;
  operaciones: number;
  total: string;
  ultimo_ingreso?: string | null;
}

export interface CostoHistoricoReporte {
  codigo: string;
  producto: string;
  proveedor: string;
  cantidad: string;
  costo_unitario: string;
  factor: string;
  fecha: string;
  documento?: string | null;
}

export interface InventarioValorizado {
  producto_id: number;
  codigo: string;
  producto: string;
  cantidad_base: string;
  costo_promedio_base: string;
  valor_costo: string;
}

export interface MargenBruto {
  desde: string;
  hasta: string;
  operaciones: number;
  ventas: string;
  costo_mercaderia_vendida: string;
  margen_bruto_estimado: string;
  margen_bruto_porcentaje: string;
  /** Nota literal del backend: el margen no es utilidad neta. */
  nota: string;
}

/* --- Configuración del negocio e impresora ------------------------------- */

export interface ConfiguracionNegocio {
  valores: Record<string, string>;
  descripciones: Record<string, string>;
}

export interface EstadoImpresora {
  activa: boolean;
  host: string;
  puerto: number;
  columnas: number;
  cortar: boolean;
  qr: boolean;
  pagina_codigo: number;
  conectada: boolean;
  mensaje: string;
}

export interface ResultadoImpresion {
  ok: boolean;
  mensaje: string;
  numero?: string;
  duracion_ms?: number;
  reimpresion?: boolean;
}

/* --- Importación de catálogo ---------------------------------------- */

export interface ResumenImportacion {
  filas: number;
  nuevos: number;
  actualizar: number;
  con_errores: number;
  con_avisos: number;
  con_stock_inicial: number;
  vinculos_proveedor: number;
}

export interface FilaImportada {
  numero: number;
  codigo: string;
  nombre: string;
  categoria: string;
  presentacion: string;
  factor_base: string;
  precio_venta: string;
  stock_inicial: string;
  proveedor_codigo: string;
  estado: string;
  mensajes: string[];
  avisos: string[];
}

export interface PrevisualizacionImportacion {
  resumen: ResumenImportacion;
  filas: FilaImportada[];
}

export interface ResultadoImportacion {
  importadas: number;
  productos_creados: number;
  productos_actualizados: number;
  rechazadas: number;
  vinculos_proveedor: number;
  stock_inicial_aplicado: number;
  aplicadas: FilaImportada[];
  errores: FilaImportada[];
}

/* --- Inventario inicial --------------------------------------------- */

export interface LineaInventarioInicial {
  producto_id: number;
  cantidad_base: string;
  costo_unitario_base: string;
}

export interface ResultadoInventarioInicial {
  total_unidades_base: string;
  lineas: {
    producto_id: number;
    producto: string;
    cantidad_base: string;
    costo_unitario_base: string;
  }[];
}

export interface AjusteInventario {
  id: number;
  numero: string;
  almacen_id: number;
  producto_id: number;
  tipo: string;
  cantidad_base: string;
  motivo: string;
  estado: string;
  created_at?: string | null;
}

/* --- Administración -------------------------------------------------- */

export interface RegistroAuditoria {
  id: number;
  actor_id?: number | null;
  accion: string;
  entidad: string;
  entidad_id?: number | null;
  detalle?: Record<string, unknown> | null;
  created_at?: string | null;
}

