import { describe, expect, it } from 'vitest';
import { nombreArchivoConPeriodo, nombreArchivoSeguro } from './descargas';

describe('nombres de archivo descargados', () => {
  it('elimina acentos y caracteres problemáticos', () => {
    expect(nombreArchivoSeguro('ventas año 2026', 'csv')).toBe('ventas-ano-2026.csv');
    expect(nombreArchivoSeguro('Informe "final"', 'csv')).toBe('Informe-final.csv');
  });

  it('usa un nombre por defecto cuando no queda texto válido', () => {
    expect(nombreArchivoSeguro('***', 'csv')).toBe('archivo.csv');
  });

  it('incluye el periodo en el nombre', () => {
    expect(nombreArchivoConPeriodo('ventas', '2026-11-01', '2026-11-30', 'csv')).toBe(
      'ventas-2026-11-01-a-2026-11-30.csv',
    );
  });

  it('omite el rango cuando desde y hasta coinciden', () => {
    expect(nombreArchivoConPeriodo('ventas', '2026-11-08', '2026-11-08', 'csv')).toBe(
      'ventas-2026-11-08.csv',
    );
  });
});
