/**
 * El cliente refleja las reglas del backend.
 *
 * Las reglas viven en los schemas del backend (`backend/app/schemas/`) y llegan
 * al cliente en `reglas.json`, que genera:
 *
 *   python -m app.core.contrato_cli --escribir
 *
 * Estas pruebas comprueban que el cliente usa ese contrato y que no se quedó
 * con reglas viejas.
 */

import { describe, expect, it } from 'vitest';
import {
  FORMAS_PAGO,
  REGLAS,
  errorDeLongitud,
  reglaDe,
  reglasDe,
} from './reglas';

describe('contrato de validaciones', () => {
  it('tiene reglas para cada pantalla que escribe datos', () => {
    const grupos = [
      'acceso',
      'usuarios',
      'productos',
      'presentaciones',
      'proveedores',
      'ventas',
      'anulacion_venta',
      'abastecimientos',
      'ajustes',
      'configuracion',
    ];
    for (const grupo of grupos) {
      expect(Object.keys(reglasDe(grupo)).length, `grupo «${grupo}» sin reglas`).toBeGreaterThan(0);
    }
  });

  it('refleja la longitud mínima de los motivos', () => {
    // El backend exige 5 caracteres en el motivo del ajuste y de la anulación.
    expect(reglaDe('ajustes', 'motivo').min).toBe(5);
    expect(reglaDe('anulacion_venta', 'motivo').min).toBe(5);
  });

  it('refleja las longitudes máximas que el backend impone', () => {
    expect(reglaDe('productos', 'codigo').max).toBe(40);
    expect(reglaDe('productos', 'nombre').max).toBe(200);
    expect(reglaDe('proveedores', 'razon_social').max).toBe(200);
    expect(reglaDe('ajustes', 'motivo').max).toBe(500);
    expect(reglaDe('anulacion_venta', 'motivo').max).toBe(500);
  });

  it('refleja las cantidades que deben ser mayores que cero', () => {
    expect(reglaDe('ventas', 'cantidad').mayor).toBe(0);
    expect(reglaDe('abastecimientos', 'cantidad').mayor).toBe(0);
    expect(reglaDe('presentaciones', 'factor_base').mayor).toBe(0);
  });

  it('refleja los precios que no pueden ser negativos', () => {
    expect(reglaDe('ventas', 'precio_total').menor_igual).toBe(0);
    expect(reglaDe('abastecimientos', 'costo_unitario').menor_igual).toBe(0);
    expect(reglaDe('productos', 'stock_minimo_base').menor_igual).toBe(0);
  });

  it('ofrece las formas de pago que el backend acepta', () => {
    expect(FORMAS_PAGO).toContain('efectivo');
    expect(FORMAS_PAGO).toContain('tarjeta');
    expect(FORMAS_PAGO).toContain('voucher');
    expect(FORMAS_PAGO).toContain('yape');
  });

  it('avisa cuando un texto es muy corto o muy largo', () => {
    const regla = reglaDe('ajustes', 'motivo');
    expect(errorDeLongitud('abc', regla, 'El motivo')).toContain('al menos 5');
    expect(errorDeLongitud('a'.repeat(600), regla, 'El motivo')).toContain('500');
    expect(errorDeLongitud('motivo correcto', regla, 'El motivo')).toBeUndefined();
  });

  it('no inventa reglas para grupos que no existen', () => {
    expect(reglasDe('grupo-que-no-existe')).toEqual({});
    expect(reglaDe('grupo-que-no-existe', 'campo')).toEqual({});
  });

  it('no tiene grupos vacíos', () => {
    const vacios = Object.entries(REGLAS)
      .filter(([, reglas]) => Object.keys(reglas).length === 0)
      .map(([grupo]) => grupo);
    expect(vacios).toEqual([]);
  });
});
