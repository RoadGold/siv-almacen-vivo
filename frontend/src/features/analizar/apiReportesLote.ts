/**
 * Reportes por lote de inventario.
 *
 * Estos dos endpoints (`/reportes/inventario-por-lote` y
 * `/reportes/ventas-por-lote`) todavía no están declarados en
 * `shared/api/endpoints.ts`, así que se llaman desde aquí con el cliente
 * HTTP común. Cuando se actualice el contrato compartido, este módulo puede
 * borrarse y dejar solo las llamadas de `reportesApi`.
 */

import { api } from '@/shared/api/client';

/** Fila del inventario desglosado por lote. */
export interface FilaInventarioLote {
  lote_id: number;
  codigo_lote: string;
  fecha_ingreso?: string | null;
  producto_codigo?: string | null;
  producto_nombre?: string | null;
  cantidad_inicial: string;
  cantidad_disponible: string;
  costo_base: string;
  costo_unitario: string;
  precio_venta: string;
  valor_costo: string;
  estado: string;
  origen: string;
}

/** Fila de ventas y rentabilidad por lote. */
export interface FilaVentasLote {
  lote_id: number;
  codigo_lote: string;
  producto_codigo?: string | null;
  producto_nombre?: string | null;
  cantidad_base: string;
  ingresos: string;
  costo: string;
  utilidad_bruta: string;
}

export const reportesLoteApi = {
  /** Inventario desglosado por lote (stock, costo y precio de cada lote). */
  inventarioPorLote: (filtros: {
    producto_id?: number | null;
    almacen_id?: number | null;
    solo_con_stock?: boolean;
    limite?: number;
  } = {}) =>
    api.get<FilaInventarioLote[]>('/reportes/inventario-por-lote', {
      producto_id: filtros.producto_id ?? undefined,
      almacen_id: filtros.almacen_id ?? undefined,
      solo_con_stock: filtros.solo_con_stock ?? undefined,
      limite: filtros.limite ?? 200,
    }),

  /** Ventas, costo y utilidad bruta agrupados por lote. */
  ventasPorLote: (filtro: { desde?: string | null; hasta?: string | null; limite?: number } = {}) =>
    api.get<FilaVentasLote[]>('/reportes/ventas-por-lote', {
      desde: filtro.desde ?? undefined,
      hasta: filtro.hasta ?? undefined,
      limite: filtro.limite ?? 200,
    }),
};
