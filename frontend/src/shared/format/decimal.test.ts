import { describe, expect, it } from 'vitest';
import { Decimal } from './decimal';

describe('Decimal', () => {
  it('evita el error binario de coma flotante al sumar', () => {
    expect(Decimal.desde('0.1').suma('0.2').aTexto()).toBe('0.3');
  });

  it('suma importes con dos decimales', () => {
    expect(Decimal.desde('12.75').suma('3.10').suma('0.15').aTexto()).toBe('16.00');
  });

  it('multiplica cantidades fraccionadas', () => {
    expect(Decimal.desde('0.75').multiplica('5').aTexto()).toBe('3.75');
    expect(Decimal.desde('0.750').multiplica('1000').aTexto()).toBe('750.000');
  });

  it('acepta coma o punto como separador decimal', () => {
    expect(Decimal.desde('0,750').multiplica('2').aTexto()).toBe('1.500');
  });

  it('redondea a la mitad hacia arriba', () => {
    expect(Decimal.desde('10.005').redondear(2).aTexto()).toBe('10.01');
    expect(Decimal.desde('-10.005').redondear(2).aTexto()).toBe('-10.01');
    expect(Decimal.desde('1234567.891').redondear(2).aTexto()).toBe('1234567.89');
  });

  it('resta y detecta valores negativos', () => {
    const resultado = Decimal.desde('5').resta('8');
    expect(resultado.aTexto()).toBe('-3');
    expect(resultado.esNegativo()).toBe(true);
    expect(resultado.esCero()).toBe(false);
  });

  it('trata entradas vacías o nulas como cero', () => {
    expect(Decimal.desde('').aTexto()).toBe('0');
    expect(Decimal.desde(null).aTexto()).toBe('0');
    expect(Decimal.desde(undefined).aTexto()).toBe('0');
    expect(Decimal.desde('no es un número').aTexto()).toBe('0');
  });

  it('compara importes con distinta escala', () => {
    expect(Decimal.desde('2.50').comparar('2.5')).toBe(0);
    expect(Decimal.desde('2.50').comparar('2.6')).toBe(-1);
    expect(Decimal.desde('3').comparar('2.6')).toBe(1);
  });
});
