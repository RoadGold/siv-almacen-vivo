/**
 * Vigila la codificacion de los archivos del frontend.
 *
 * Revisa que no queden restos de doble codificacion (una vocal acentuada se
 * convierte en dos caracteres), que aparecerian como texto roto en la interfaz.
 */

import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const INDICADORES = /[\u00c2\u00c3][\u0080-\u00bf]|[\u00e2]\u20ac|[\u00ef]\u00bb\u00bf|\ufffd/g;

const RAIZ = join(process.cwd(), 'src');
const EXTENSIONES = ['.ts', '.tsx', '.css', '.html', '.js', '.json'];

function archivos(directorio: string): string[] {
  const encontrados: string[] = [];
  for (const entrada of readdirSync(directorio)) {
    const completa = join(directorio, entrada);
    if (statSync(completa).isDirectory()) {
      encontrados.push(...archivos(completa));
    } else if (EXTENSIONES.some((extension) => entrada.endsWith(extension))) {
      encontrados.push(completa);
    }
  }
  return encontrados;
}

describe('codificacion del frontend', () => {
  const lista = archivos(RAIZ);

  it('hay archivos que revisar', () => {
    expect(lista.length).toBeGreaterThan(20);
  });

  it('ningun archivo tiene doble codificacion', () => {
    const problemas: string[] = [];
    for (const ruta of lista) {
      if (ruta.endsWith('codificacion.test.ts')) continue;
      const texto = readFileSync(ruta, 'utf8');
      const coincidencias = texto.match(INDICADORES);
      if (coincidencias) {
        problemas.push(`${ruta.replace(process.cwd(), '')}: ${coincidencias.length}`);
      }
    }
    expect(problemas).toEqual([]);
  });
});
