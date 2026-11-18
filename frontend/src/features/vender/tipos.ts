/** Tipos de la pantalla de venta. */

export interface LineaCarrito {
  /** Identificador local de la línea (no es el id del servidor). */
  id: string;
  producto_id: number;
  presentacion_id: number;
  producto_nombre: string;
  producto_codigo: string;
  presentacion_nombre: string;
  unidad_base: string | null;
  factor_base: string;
  /** Precio unitario de lista del lote (referencia, no editable). */
  precio_original: string;
  /** Total a cobrar por la línea: es lo que se edita en la caja. */
  precio_total: string;
  /** Total de lista de la línea (cantidad × precio original). */
  precio_total_original: string;
  /** Motivo opcional del cambio de precio. */
  motivo_precio?: string | null;
  /** Cantidad en la presentación elegida, como texto decimal. */
  cantidad: string;
  /** Lote de origen (si el producto se maneja por lotes). */
  lote_id?: number | null;
  lote_codigo?: string | null;
  lote_fecha_ingreso?: string | null;
}

export interface ResultadoBusqueda {
  producto_id: number;
  codigo: string;
  nombre: string;
  unidad_base: string | null;
  /** Stock disponible en unidad base. */
  stock_base: string;
  estado: string;
  presentacion_principal: string | null;
  cantidad_presentacion: string | null;
  presentaciones: import('@/shared/types/api').Presentacion[];
}
