import { describe, expect, it } from 'vitest';
import {
  abreviarUnidad,
  etiquetaEstado,
  etiquetaTipoMovimiento,
  formatearCantidad,
  formatearCantidadConSigno,
  formatearEnUnidadLegible,
  formatearFecha,
  formatearMoneda,
  formatearNumero,
  formatearPorcentaje,
  haceDiasISO,
  hoyISO,
  inicioMesISO,
} from './formato';

describe('formatos locales peruanos', () => {
  it('formatea la moneda con S/ y coma decimal', () => {
    expect(formatearMoneda('1234.5')).toBe('S/ 1\u00a0234,50');
    expect(formatearMoneda('1234567.891')).toBe('S/ 1\u00a0234\u00a0567,89');
  });

  it('formatea números con separador de miles', () => {
    expect(formatearNumero('980.5', 2)).toBe('980,50');
    expect(formatearNumero('1000', 0)).toBe('1\u00a0000');
  });

  it('mantiene la precisión de las cantidades', () => {
    expect(formatearCantidad('208')).toBe('208');
    expect(formatearCantidad('208.000')).toBe('208');
    expect(formatearCantidad('45.500')).toBe('45,500');
    expect(formatearCantidad('0.750')).toBe('0,750');
  });

  it('muestra el signo de las cantidades', () => {
    expect(formatearCantidadConSigno('-750')).toBe('\u2212750');
    expect(formatearCantidadConSigno('240')).toBe('+240');
    expect(formatearCantidadConSigno('0')).toBe('0');
  });

  it('expresa el stock en la unidad legible', () => {
    expect(formatearEnUnidadLegible('750', 'Gramo')).toBe('750 g');
    expect(formatearEnUnidadLegible('45500', 'Gramo')).toBe('45,500 kg');
    expect(formatearEnUnidadLegible('208', 'Unidad')).toBe('208 unidades');
    expect(formatearEnUnidadLegible('1', 'Unidad')).toBe('1 unidad');
    expect(formatearEnUnidadLegible('2000', 'Mililitro')).toBe('2 L');
  });

  it('abrevia las unidades en las cabeceras de tabla', () => {
    expect(abreviarUnidad('Kilogramo')).toBe('kg');
    expect(abreviarUnidad('Mililitro')).toBe('ml');
    expect(abreviarUnidad(null)).toBe('und');
  });

  it('nombra los estados para no depender solo del color', () => {
    expect(etiquetaEstado('agotado')).toBe('Agotado');
    expect(etiquetaEstado('bajo_minimo')).toBe('Bajo mínimo');
    expect(etiquetaEstado('disponible')).toBe('Disponible');
    expect(etiquetaTipoMovimiento('REVERSO_VENTA')).toBe('Anulación de venta');
  });

  it('muestra las fechas en formato local', () => {
    expect(formatearFecha('2026-11-08')).toBe('08/11/2026');
  });

  it('formatea porcentajes con coma decimal', () => {
    expect(formatearPorcentaje('12.345')).toBe('12,35 %');
    expect(formatearPorcentaje('0')).toBe('0,00 %');
  });

  it('calcula las fechas de los atajos de periodo', () => {
    expect(hoyISO()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(inicioMesISO().endsWith('-01')).toBe(true);
    expect(haceDiasISO(0)).toBe(hoyISO());
    expect(haceDiasISO(29) < hoyISO()).toBe(true);
  });
});
