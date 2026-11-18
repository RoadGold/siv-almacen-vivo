/**
 * Pruebas de la sección de lotes de la ficha del producto.
 */

import { describe, expect, it } from 'vitest';
import { estadoLote } from './SeccionLotes';
import type { LoteResumen } from '@/shared/types/api';

function lote(estado: string): LoteResumen {
  return {
    id: 1,
    producto_id: 1,
    codigo_lote: 'L001',
    fecha_ingreso: '2026-01-15',
    cantidad_inicial: '10',
    cantidad_disponible: '10',
    costo_base: '8',
    costo_unitario: '8',
    precio_venta: '12.00',
    almacen_id: 1,
    estado,
    origen: 'RECEPCION',
    precios: [],
    tiene_precios_distintos: false,
  };
}

describe('estado de un lote', () => {
  it('muestra los lotes agotados con su etiqueta', () => {
    expect(estadoLote(lote('AGOTADO'))).toEqual({ texto: 'Agotado', tono: 'peligro' });
  });

  it('muestra los lotes disponibles', () => {
    expect(estadoLote(lote('ACTIVO'))).toEqual({ texto: 'Disponible', tono: 'marca' });
  });

  it('muestra los lotes inhabilitados', () => {
    expect(estadoLote(lote('INHABILITADO'))).toEqual({
      texto: 'Inhabilitado',
      tono: 'neutro',
    });
  });
});
