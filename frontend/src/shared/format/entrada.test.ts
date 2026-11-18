/**
 * Pruebas de la lectura de números escritos por una persona.
 */

import { describe, expect, it } from 'vitest';
import { esNumeroValido, parsearEntradaNumerica } from './entrada';

describe('parsearEntradaNumerica', () => {
  it('entiende los miles con punto, espacio o coma', () => {
    expect(parsearEntradaNumerica('1.000')).toBe('1000');
    expect(parsearEntradaNumerica('1 000')).toBe('1000');
    expect(parsearEntradaNumerica('1,000')).toBe('1000');
    expect(parsearEntradaNumerica('12.500')).toBe('12500');
    expect(parsearEntradaNumerica('1.234.567')).toBe('1234567');
  });

  it('entiende los decimales con coma', () => {
    expect(parsearEntradaNumerica('12,50')).toBe('12.50');
    expect(parsearEntradaNumerica('0,750')).toBe('0.750');
    expect(parsearEntradaNumerica('3,4')).toBe('3.4');
  });

  it('entiende los decimales con punto', () => {
    expect(parsearEntradaNumerica('1.5')).toBe('1.5');
    expect(parsearEntradaNumerica('0.75')).toBe('0.75');
  });

  it('entiende el formato mixto', () => {
    expect(parsearEntradaNumerica('1.234,56')).toBe('1234.56');
  });

  it('deja intactos los números simples', () => {
    expect(parsearEntradaNumerica('10')).toBe('10');
    expect(parsearEntradaNumerica('0')).toBe('0');
    expect(parsearEntradaNumerica('170.00')).toBe('170.00');
  });

  it('devuelve vacío cuando no hay número', () => {
    expect(parsearEntradaNumerica('')).toBe('');
    expect(parsearEntradaNumerica('   ')).toBe('');
    expect(parsearEntradaNumerica('abc')).toBe('');
    expect(parsearEntradaNumerica('1,2,3')).toBe('');
  });

  it('valida números', () => {
    expect(esNumeroValido('1.000')).toBe(true);
    expect(esNumeroValido('')).toBe(false);
    expect(esNumeroValido('doce')).toBe(false);
  });

  it('entiende el signo menos de los ajustes de stock', () => {
    expect(parsearEntradaNumerica('-2')).toBe('-2');
    expect(parsearEntradaNumerica('-2,50')).toBe('-2.50');
    expect(parsearEntradaNumerica('-1.000')).toBe('-1000');
    expect(parsearEntradaNumerica('-0,750')).toBe('-0.750');
  });
});
