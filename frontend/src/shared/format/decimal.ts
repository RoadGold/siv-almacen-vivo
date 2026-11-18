/**
 * Aritmética decimal exacta para SIV · Almacén Vivo.
 *
 * La API devuelve todos los importes y cantidades como cadenas decimales.
 * Nunca se convierten con `parseFloat` ni se suman con `+` sobre `number`:
 * un `float` binario introduce errores de redondeo en el dinero.
 *
 * Esta implementación representa un decimal como un entero grande (`bigint`)
 * accompanied de su escala (número de decimales), de modo que
 * `sumar`, `restar` y `multiplicar` son operaciones exactas.
 */

import { parsearEntradaNumerica } from './entrada';

export type EntradaDecimal = string | number | bigint | Decimal | null | undefined;

const REGEX_DECIMAL = /^([+-]?)(\d*)(?:[.,](\d*))?$/;

export class Decimal {
  /** Valor escalado: `unidades / 10 ** escala`. */
  readonly unidades: bigint;
  readonly escala: number;

  private constructor(unidades: bigint, escala: number) {
    this.unidades = unidades;
    this.escala = escala;
  }

  /** Construye un decimal desde texto, número o `Decimal`. */
  static desde(valor: EntradaDecimal): Decimal {
    if (valor instanceof Decimal) return valor;
    if (valor === null || valor === undefined) return new Decimal(0n, 0);
    if (typeof valor === 'bigint') return new Decimal(valor, 0);
    if (typeof valor === 'number') {
      if (!Number.isFinite(valor)) return new Decimal(0n, 0);
      return Decimal.desde(numeroATexto(valor));
    }

    const texto = String(valor).trim().replace(/\s+/g, '');
    if (texto === '') return new Decimal(0n, 0);

    const coincidencia = REGEX_DECIMAL.exec(texto);
    if (!coincidencia) return new Decimal(0n, 0);

    const signo = coincidencia[1] === '-' ? -1n : 1n;
    const entero = coincidencia[2] || '0';
    const fraccion = coincidencia[3] || '';
    const digitos = `${entero}${fraccion}`.replace(/^0+(?=\d)/, '') || '0';
    return new Decimal(signo * BigInt(digitos), fraccion.length);
  }

  static cero(): Decimal {
    return new Decimal(0n, 0);
  }

  /**
   * Convierte **lo que escribe una persona** en decimal.
   *
   * Entiende la notación de miles (`1.000` son mil) igual que la caja. Si el
   * texto no es un número, devuelve `null` en vez de `0`: así el error se ve
   * en vez de guardarse un cero calladito.
   */
  static intentarDesde(texto: string): Decimal | null {
    const normalizado = parsearEntradaNumerica(texto);
    if (normalizado === '') return null;
    return Decimal.desde(normalizado);
  }

  /** Alinea dos decimales a la misma escala. */
  private static alinear(a: Decimal, b: Decimal): [bigint, bigint, number] {
    const escala = Math.max(a.escala, b.escala);
    const factor = 10n ** BigInt(escala - a.escala);
    const factorB = 10n ** BigInt(escala - b.escala);
    return [a.unidades * factor, b.unidades * factorB, escala];
  }

  suma(otro: EntradaDecimal): Decimal {
    const [ua, ub, escala] = Decimal.alinear(this, Decimal.desde(otro));
    return new Decimal(ua + ub, escala);
  }

  resta(otro: EntradaDecimal): Decimal {
    const [ua, ub, escala] = Decimal.alinear(this, Decimal.desde(otro));
    return new Decimal(ua - ub, escala);
  }

  multiplica(otro: EntradaDecimal): Decimal {
    const b = Decimal.desde(otro);
    return new Decimal(this.unidades * b.unidades, this.escala + b.escala);
  }

  /**
   * División exacta con la escala indicada (redondeo «half up»).
   *
   * this / b = (this.unidades / b.unidades) · 10^(b.escala − this.escala)
   * Para expresar el resultado con `decimales` decimales:
   *   numerador   = this.unidades · 10^(b.escala + decimales)
   *   denominador = b.unidades   · 10^this.escala
   * Si el divisor es cero, devuelve cero en la escala pedida.
   */
  divide(otro: EntradaDecimal, decimales = 6): Decimal {
    const b = Decimal.desde(otro);
    if (b.unidades === 0n) return new Decimal(0n, decimales);
    const numerador = this.unidades * 10n ** BigInt(b.escala + decimales);
    const denominador = b.unidades * 10n ** BigInt(this.escala);
    const negativo = (numerador < 0n) !== (denominador < 0n);
    const absoluto = numerador < 0n ? -numerador : numerador;
    const divisor = denominador < 0n ? -denominador : denominador;
    const entero = absoluto / divisor;
    const resto = absoluto % divisor;
    const redondeado = resto * 2n >= divisor ? entero + 1n : entero;
    return new Decimal(negativo ? -redondeado : redondeado, decimales);
  }

  /** Redondeo «half up» (mitad hacia arriba) a la cantidad de decimales indicada. */
  redondear(decimales: number): Decimal {
    if (decimales < 0) decimales = 0;
    if (this.escala <= decimales) {
      const factor = 10n ** BigInt(decimales - this.escala);
      return new Decimal(this.unidades * factor, decimales);
    }
    const factor = 10n ** BigInt(this.escala - decimales);
    const negativo = this.unidades < 0n;
    const absoluto = negativo ? -this.unidades : this.unidades;
    // `entero` ya queda expresado con la escala destino (10^decimales).
    const entero = absoluto / factor;
    const resto = absoluto % factor;
    const redondeado = resto * 2n >= factor ? entero + 1n : entero;
    return new Decimal(negativo ? -redondeado : redondeado, decimales);
  }

  esNegativo(): boolean {
    return this.unidades < 0n;
  }

  esCero(): boolean {
    return this.unidades === 0n;
  }

  comparar(otro: EntradaDecimal): number {
    const [ua, ub] = Decimal.alinear(this, Decimal.desde(otro));
    if (ua < ub) return -1;
    if (ua > ub) return 1;
    return 0;
  }

  /** Texto plano con la escala actual (sin separadores). */
  aTexto(decimales?: number): string {
    const valor = decimales === undefined ? this : this.redondear(decimales);
    const negativo = valor.unidades < 0n;
    const absoluto = negativo ? -valor.unidades : valor.unidades;
    const base = 10n ** BigInt(valor.escala);
    const entero = absoluto / base;
    let texto = entero.toString();
    if (valor.escala > 0) {
      texto += `.${(absoluto % base).toString().padStart(valor.escala, '0')}`;
    }
    return `${negativo ? '-' : ''}${texto}`;
  }

  /** Representación aproximada en `number`; solo para gráficos y cálculos no monetarios. */
  aNumero(): number {
    return Number(this.aTexto());
  }
}

/** Convierte un `number` a texto decimal plano (sin notación científica). */
function numeroATexto(valor: number): string {
  const texto = String(valor);
  if (!/[eE]/.test(texto)) return texto;

  const [mantisa, exponenteTexto] = texto.split(/[eE]/);
  const exponente = Number(exponenteTexto);
  const signo = mantisa.startsWith('-') ? '-' : '';
  const [entero, decimal] = mantisa.replace('-', '').split('.');
  const digitos = `${entero ?? '0'}${decimal ?? ''}`;
  const punto = (entero ?? '0').length + exponente;

  if (punto <= 0) return `${signo}0.${'0'.repeat(-punto)}${digitos}`;
  if (punto >= digitos.length) return `${signo}${digitos}${'0'.repeat(punto - digitos.length)}`;
  return `${signo}${digitos.slice(0, punto)}.${digitos.slice(punto)}`;
}

/** Suma una lista de decimales (texto o número) sin perder precisión. */
export function sumar(valores: EntradaDecimal[]): Decimal {
  return valores.reduce<Decimal>((total, valor) => total.suma(valor), Decimal.cero());
}

/** Suma los importes de una lista de objetos que tienen la propiedad `importe`. */
export function sumarImportes<T extends Record<string, EntradaDecimal>>(
  filas: T[],
  propiedad: keyof T,
): Decimal {
  return filas.reduce<Decimal>((total, fila) => total.suma(fila[propiedad]), Decimal.cero());
}
