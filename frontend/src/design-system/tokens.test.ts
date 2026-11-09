/**
 * Verificación automática del contraste de la paleta (WCAG AA).
 *
 * Se leen los tokens reales de `tokens.css` y se comprueba que cada par de
 * texto y fondo cumpla el contraste mínimo, tanto en el tema claro como en
 * el oscuro. Si alguien cambia un color sin revisar el contraste, la prueba
 * falla.
 */

import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const aqui = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(aqui, 'tokens.css'), 'utf8');

function bloque(inicio: string): string {
  const desde = css.indexOf(inicio);
  expect(desde, `no se encontró el bloque ${inicio}`).toBeGreaterThan(-1);
  const fin = css.indexOf('}', desde);
  return css.slice(desde, fin);
}

function tokensDe(bloqueCss: string): Record<string, string> {
  const resultado: Record<string, string> = {};
  const patron = /--([a-z-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;/g;
  let coincidencia = patron.exec(bloqueCss);
  while (coincidencia) {
    resultado[coincidencia[1]] = coincidencia[2];
    coincidencia = patron.exec(bloqueCss);
  }
  return resultado;
}

function aRgb(hex: string): [number, number, number] {
  let valor = hex.replace('#', '');
  if (valor.length === 3) {
    valor = valor
      .split('')
      .map((c) => c + c)
      .join('');
  }
  return [
    parseInt(valor.slice(0, 2), 16),
    parseInt(valor.slice(2, 4), 16),
    parseInt(valor.slice(4, 6), 16),
  ];
}

function luminancia(hex: string): number {
  const canales = aRgb(hex).map((canal) => {
    const valor = canal / 255;
    return valor <= 0.03928 ? valor / 12.92 : ((valor + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2];
}

/** Razón de contraste entre dos colores, de 1 a 21. */
export function contraste(primero: string, segundo: string): number {
  const l1 = luminancia(primero);
  const l2 = luminancia(segundo);
  const claro = Math.max(l1, l2);
  const oscuro = Math.min(l1, l2);
  return (claro + 0.05) / (oscuro + 0.05);
}

const claro = tokensDe(bloque(':root'));
const oscuro = tokensDe(bloque("[data-tema='oscuro']"));

/** Pares que deben cumplir contraste AA (4.5:1) para texto normal. */
const PARES_TEXTO: [string, string][] = [
  ['ink', 'canvas'],
  ['ink', 'surface'],
  ['ink', 'surface-tenue'],
  ['ink-suave', 'canvas'],
  ['ink-suave', 'surface'],
  ['muted', 'canvas'],
  ['muted', 'surface'],
  ['brand', 'surface'],
  ['brand', 'canvas'],
  ['danger', 'surface'],
  ['warning', 'surface'],
  ['ink', 'brand-tenue'],
  ['ink', 'accent-tenue'],
  ['ink', 'warning-tenue'],
  ['ink', 'danger-tenue'],
  ['sobre-brand', 'brand'],
  ['sobre-ink', 'ink'],
];

describe('paleta del tema claro', () => {
  for (const [texto, fondo] of PARES_TEXTO) {
    it(`${texto} sobre ${fondo} cumple AA`, () => {
      const razon = contraste(claro[texto], claro[fondo]);
      expect(razon, `${texto} sobre ${fondo}: ${razon.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5);
    });
  }
});

describe('paleta del tema oscuro', () => {
  for (const [texto, fondo] of PARES_TEXTO) {
    it(`${texto} sobre ${fondo} cumple AA`, () => {
      const razon = contraste(oscuro[texto], oscuro[fondo]);
      expect(razon, `${texto} sobre ${fondo}: ${razon.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5);
    });
  }
});

describe('bordes y elementos de interfaz', () => {
  it('las líneas se distinguen del fondo en ambos temas', () => {
    expect(contraste(claro['linea-fuerte'], claro['surface'])).toBeGreaterThan(1.2);
    expect(contraste(oscuro['linea-fuerte'], oscuro['surface'])).toBeGreaterThan(1.2);
  });

  it('el estado de conexión se distingue del fondo', () => {
    expect(contraste(claro['danger'], claro['canvas'])).toBeGreaterThanOrEqual(4.5);
    expect(contraste(oscuro['danger'], oscuro['canvas'])).toBeGreaterThanOrEqual(4.5);
  });
});
