/**
 * Pruebas de la lógica de selección de lotes (PEPS) de la caja.
 */

import { describe, expect, it } from 'vitest';
import { precioDeLote, repartoSugerido } from './SelectorLote';
import type { LoteResumen } from '@/shared/types/api';

function lote(
  id: number,
  codigo: string,
  stock: string,
  precio: string,
  fecha: string | null = '2026-01-15',
): LoteResumen {
  return {
    id,
    producto_id: 1,
    codigo_lote: codigo,
    fecha_ingreso: fecha,
    cantidad_inicial: stock,
    cantidad_disponible: stock,
    costo_base: '8',
    costo_unitario: '8',
    precio_venta: precio,
    almacen_id: 1,
    estado: 'ACTIVO',
    origen: 'RECEPCION',
    precios: [{ presentacion_id: 1, presentacion_nombre: 'botella', precio }],
    precio_minimo: precio,
    precio_maximo: precio,
    tiene_precios_distintos: false,
  };
}

describe('precio de un lote', () => {
  it('usa el precio de la presentacion del lote', () => {
    const l = lote(1, 'L001', '10', '12.00');
    expect(precioDeLote(l, 1).aTexto()).toBe('12.00');
  });

  it('si el lote no tiene ese precio, usa el precio del lote', () => {
    const l = lote(1, 'L001', '10', '12.00');
    l.precios = [];
    expect(precioDeLote(l, 9).aTexto()).toBe('12.00');
  });
});

describe('reparto sugerido (PEPS)', () => {
  it('completa con el lote mas antiguo', () => {
    const lotes = [lote(1, 'L001', '10', '12.00'), lote(2, 'L002', '20', '14.00')];
    const { suggested } = repartoSugerido(lotes, 1, '6');
    expect(suggested.get(1)).toBe('6');
    expect(suggested.get(2)).toBeUndefined();
  });

  it('reparte entre varios lotes cuando el primero no alcanza', () => {
    const lotes = [lote(1, 'L001', '8', '12.00'), lote(2, 'L002', '20', '14.00')];
    const { suggested } = repartoSugerido(lotes, 1, '12');
    expect(suggested.get(1)).toBe('8');
    expect(suggested.get(2)).toBe('4');
  });

  it('ignora los lotes agotados', () => {
    const lotes = [lote(1, 'L001', '0', '12.00'), lote(2, 'L002', '20', '14.00')];
    const { suggested } = repartoSugerido(lotes, 1, '5');
    expect(suggested.get(1)).toBeUndefined();
    expect(suggested.get(2)).toBe('5');
  });

  it('no asigna mas de lo disponible', () => {
    const lotes = [lote(1, 'L001', '3', '12.00')];
    const { suggested, restante } = repartoSugerido(lotes, 1, '10');
    expect(suggested.get(1)).toBe('3');
    expect(restante.aTexto()).toBe('7');
  });
});
