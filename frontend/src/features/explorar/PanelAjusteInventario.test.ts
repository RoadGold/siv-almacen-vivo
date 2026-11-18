/**
 * Pruebas de la elección de lote en el ajuste de inventario.
 */

import { describe, expect, it } from 'vitest';
import { loteAfectado, lotesConExistencias } from './PanelAjusteInventario';
import type { LoteResumen } from '@/shared/types/api';

function lote(id: number, codigo: string, stock: string): LoteResumen {
  return {
    id,
    producto_id: 1,
    codigo_lote: codigo,
    fecha_ingreso: '2026-01-15',
    cantidad_inicial: stock,
    cantidad_disponible: stock,
    costo_base: '8',
    costo_unitario: '8',
    precio_venta: '12.00',
    almacen_id: 1,
    estado: stock === '0' ? 'AGOTADO' : 'ACTIVO',
    origen: 'RECEPCION',
    precios: [{ presentacion_id: 1, presentacion_nombre: 'botella', precio: '12.00' }],
    precio_minimo: '12.00',
    precio_maximo: '12.00',
    tiene_precios_distintos: false,
  };
}

describe('lotes con existencias', () => {
  it('descarta los lotes agotados', () => {
    const resultado = lotesConExistencias([
      lote(1, 'L001', '10'),
      lote(2, 'L002', '0'),
      lote(3, 'L003', '4.5'),
    ]);
    expect(resultado.map((item) => item.codigo_lote)).toEqual(['L001', 'L003']);
  });

  it('no considera los lotes con stock cero ni negativo', () => {
    expect(lotesConExistencias([lote(1, 'L001', '0')])).toHaveLength(0);
  });
});

describe('lote afectado por el ajuste', () => {
  it('elige solo el lote cuando hay uno con existencias', () => {
    const unLote = [lote(1, 'L001', '10')];
    expect(loteAfectado(unLote, '')?.codigo_lote).toBe('L001');
  });

  it('exige elegir un lote cuando hay varios con existencias', () => {
    const varios = [lote(1, 'L001', '10'), lote(2, 'L002', '5')];
    expect(loteAfectado(varios, '')).toBeNull();
    expect(loteAfectado(varios, 2)?.codigo_lote).toBe('L002');
  });

  it('no devuelve un lote que no tiene existencias', () => {
    const varios = [lote(1, 'L001', '10'), lote(2, 'L002', '5')];
    expect(loteAfectado(varios, 99)).toBeNull();
  });

  it('sin lotes con existencias no hay lote afectado', () => {
    expect(loteAfectado([], 1)).toBeNull();
  });
});
