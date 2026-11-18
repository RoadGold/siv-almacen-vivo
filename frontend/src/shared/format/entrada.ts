/**
 * Lectura de números escritos por una persona.
 *
 * El sistema muestra los importes como «1 234,56» (espacio de miles, coma
 * decimal). Al escribir, la persona puede usar esa notación o la corriente
 * («1.000», «1,000», «1 000»). Esta función entiende todas las formas y
 * devuelve el texto normalizado con punto decimal, que es lo que espera la API.
 *
 * Reglas (decididas con el negocio):
 *   1.000  ·  1 000  ·  1,000   ->  1000   (miles)
 *   12,50                       ->  12.50  (decimal)
 *   0,750                       ->  0.750  (decimal: la parte entera es 0)
 *   1.5                        ->  1.5    (decimal)
 *   1.234.567                  ->  1234567 (miles)
 */

/** Quita los espacios (incluidos los finos) que separan los miles. */
function quitarEspacios(texto: string): string {
  return texto.replace(/[\s\u00a0\u202f\u2009]/g, '');
}

/**
 * Normaliza un texto numérico escrito por una persona.
 * Devuelve '' si no se puede interpretar como número.
 */
export function parsearEntradaNumerica(texto: string): string {
  let limpio = quitarEspacios(texto ?? '');
  if (limpio === '') return '';

  const tieneComa = limpio.includes(',');
  const tienePunto = limpio.includes('.');

  if (tieneComa && tienePunto) {
    // 1.234,56 -> el punto es de miles y la coma es decimal.
    limpio = limpio.replace(/\./g, '').replace(',', '.');
  } else if (tieneComa) {
    const [entero, ...resto] = limpio.split(',');
    const decimales = resto.join(',');
    if (
      decimales.length === 3 &&
      entero.length >= 1 &&
      entero.length <= 3 &&
      entero !== '0'
    ) {
      // 1,000 -> miles (tres dígitos y parte entera de 1 a 3).
      limpio = entero + decimales;
    } else {
      // 12,50 -> decimal ; 0,750 -> decimal.
      limpio = `${entero}.${decimales}`;
    }
  } else if (tienePunto) {
    const partes = limpio.split('.');
    const decimales = partes.slice(1);
    if (
      partes.length > 1 &&
      decimales.every((parte) => parte.length === 3) &&
      partes[0].length >= 1 &&
      partes[0].length <= 3 &&
      partes[0] !== '0'
    ) {
      // 1.000 -> miles ; 1.234.567 -> millones.
      limpio = partes.join('');
    }
    // En cualquier otro caso, el punto ya es decimal.
  }

  if (!/^\d*\.?\d*$/.test(limpio) || limpio === '' || limpio === '.') {
    return '';
  }
  return limpio;
}

/** Indica si el texto es un número válido (tras normalizarlo). */
export function esNumeroValido(texto: string): boolean {
  return parsearEntradaNumerica(texto) !== '';
}
