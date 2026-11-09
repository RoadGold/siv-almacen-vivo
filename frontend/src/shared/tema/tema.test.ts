/**
 * Pruebas de la lógica del tema visual.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ETIQUETAS,
  aplicarTema,
  guardarPreferencia,
  preferenciaGuardada,
  resolverTema,
  sistemaPrefiereOscuro,
} from './tema';

function simularSistema(oscuro: boolean, almacenado?: string) {
  const local = new Map<string, string>();
  if (almacenado !== undefined) local.set('siv.tema', almacenado);

  vi.stubGlobal('window', {
    localStorage: {
      getItem: (clave: string) => local.get(clave) ?? null,
      setItem: (clave: string, valor: string) => local.set(clave, valor),
    },
    matchMedia: (consulta: string) => ({
      matches: consulta.includes('dark') ? oscuro : false,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }),
  });

  return {
    recuperar: () => local.get('siv.tema'),
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('tema visual', () => {
  it('respeta las preferencias explícitas', () => {
    simularSistema(false);
    expect(resolverTema('oscuro')).toBe('oscuro');
    expect(resolverTema('claro')).toBe('claro');
  });

  it('sigue al sistema cuando la preferencia es «sistema»', () => {
    simularSistema(true);
    expect(resolverTema('sistema')).toBe('oscuro');
    expect(sistemaPrefiereOscuro()).toBe(true);

    simularSistema(false);
    expect(resolverTema('sistema')).toBe('claro');
    expect(sistemaPrefiereOscuro()).toBe(false);
  });

  it('guarda y recupera la preferencia', () => {
    const almacen = simularSistema(false);
    guardarPreferencia('oscuro');
    expect(almacen.recuperar()).toBe('oscuro');
    expect(preferenciaGuardada()).toBe('oscuro');
  });

  it('usa la preferencia del sistema cuando no hay nada guardado', () => {
    simularSistema(false);
    expect(preferenciaGuardada()).toBe('sistema');
  });

  it('expone textos para todas las opciones', () => {
    expect(ETIQUETAS.claro).toBeTruthy();
    expect(ETIQUETAS.oscuro).toBeTruthy();
    expect(ETIQUETAS.sistema).toBeTruthy();
  });

  it('aplica el tema como atributo del documento', () => {
    const dataset: Record<string, string> = {};
    vi.stubGlobal('document', { documentElement: { dataset, style: {} } });
    aplicarTema('oscuro');
    expect(dataset.tema).toBe('oscuro');
    aplicarTema('claro');
    expect(dataset.tema).toBe('claro');
  });
});
