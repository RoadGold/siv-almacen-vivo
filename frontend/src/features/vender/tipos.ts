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
  precio_unitario: string;
  /** Cantidad en la presentación elegida, como texto decimal. */
  cantidad: string;
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
