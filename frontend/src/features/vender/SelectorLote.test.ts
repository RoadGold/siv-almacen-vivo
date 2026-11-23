/**
 * Pruebas de la lógica de selección de lotes (PEPS) de la caja.
 */

import { describe, expect, it } from 'vitest';
import {
  disponibleEnPresentacion,
  ordenDeLotes,
  precioDeLote,
  repartoSugerido,
} from './SelectorLote';
import type { LoteResumen } from '@/shared/types/api';

function lote(
  id: number,
  codigo: string,
  stock: string,
  precio: string,
  fecha: string | null = '2026-01-15',
  presentacionId: number | null = 1,
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
    presentacion_id: presentacionId,
    presentacion_nombre: presentacionId === 2 ? 'saco 40 kg pellet' : 'saco 20 kg pellet',
    factor_base: presentacionId === 2 ? '40000' : '20000',
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

  it('convierte stock base en gramos a sacos y medios sacos al repartir entre lotes', () => {
    // Lote 1 tiene medio saco (20 000 g) y Lote 2 tiene 5 sacos (200 000 g).
    const lotes = [lote(1, 'L001', '20000', '110.00'), lote(2, 'L002', '200000', '115.00')];
    const { suggested, restante } = repartoSugerido(lotes, 1, '1', '40000');
    expect(suggested.get(1)).toBe('0.5');
    expect(suggested.get(2)).toBe('0.5');
    expect(restante.aTexto()).toBe('0');
  });

  it('propone primero el lote cuya presentacion coincide con la de venta', () => {
    // Lote 1 es de sacos de 20 kg (mas antiguo) y Lote 2 de sacos de 40 kg.
    const lotes = [lote(1, 'L001', '280000', '78.00', '2026-01-15', 1)];
    lotes.push(lote(2, 'L002', '280000', '153.40', '2026-11-22', 2));

    // Se vende un saco de 40 kg: se propone el lote de 40 kg, no el de 20 kg.
    const { suggested } = repartoSugerido(lotes, 2, '1', '40000');
    expect(suggested.get(2)).toBe('1');
    expect(suggested.get(1)).toBeUndefined();
  });

  it('descunta del stock lo que ya esta en el carrito de ese lote', () => {
    const lotes = [lote(1, 'L001', '20000', '110.00', '2026-01-15', 1)];
    // Del lote solo quedan 10 000 g libres (ya se ruth vendieron 10 000 g).
    const disponible = disponibleEnPresentacion(lotes[0], '20000', '10000');
    expect(disponible.comparar('0.5')).toBe(0);

    // El reparto no puede ofrecer mas de lo que queda.
    const { suggested, restante } = repartoSugerido(lotes, 1, '1', '20000', { 1: '10000' });
    expect(suggested.get(1)).toBe('0.5');
    expect(restante.aTexto()).toBe('0.5');
  });

  it('no ofrece un lote que ya se agoto en el carrito', () => {
    const lotes = [lote(1, 'L001', '20000', '110.00', '2026-01-15', 1)];
    const { suggested, restante } = repartoSugerido(lotes, 1, '1', '20000', { 1: '20000' });
    expect(suggested.get(1)).toBeUndefined();
    expect(restante.aTexto()).toBe('1');
  });

  it('ordena los lotes por presentacion que coincide y despues por antiguedad', () => {
    const lotes = [
      lote(1, 'L001', '100', '10.00', '2026-01-15', 1),
      lote(2, 'L002', '100', '10.00', '2026-02-20', 1),
      lote(3, 'L003', '100', '10.00', '2026-03-25', 2),
    ];
    const orden = ordenDeLotes(lotes, 2).map((item) => item.id);
    expect(orden).toEqual([3, 1, 2]);
  });
});
