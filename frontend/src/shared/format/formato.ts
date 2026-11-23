/**
 * Formatos de presentación para SIV · Almacén Vivo.
 *
 * Convención local peruana:
 *  · moneda `S/`
 *  · separador de miles: espacio fino (no separable)
 *  · separador decimal: coma
 *  · fechas en `dd/mm/aaaa`
 */

import { Decimal, type EntradaDecimal } from './decimal';

export const SEPARADOR_MILES = '\u00A0';
export const SIMBOLO_MONEDA = 'S/';

/** Divide el entero en grupos de tres con el separador de miles local. */
function conSeparadorMiles(entero: string): string {
  const negativo = entero.startsWith('-');
  const digitos = negativo ? entero.slice(1) : entero;
  const grupos = digitos.replace(/\B(?=(\d{3})+(?!\d))/g, SEPARADOR_MILES);
  return `${negativo ? '-' : ''}${grupos}`;
}

/** Formatea un decimal como número local (coma decimal, miles con espacio). */
export function formatearNumero(valor: EntradaDecimal, decimales = 2): string {
  const texto = Decimal.desde(valor).redondear(decimales).aTexto(decimales);
  const [entero, fraccion] = texto.split('.');
  return fraccion
    ? `${conSeparadorMiles(entero)},${fraccion}`
    : conSeparadorMiles(entero);
}

/** Formatea un importe con la moneda local: `S/ 1 234,50`. */
export function formatearMoneda(valor: EntradaDecimal, decimales = 2): string {
  return `${SIMBOLO_MONEDA} ${formatearNumero(valor, decimales)}`;
}

/**
 * Formatea una cantidad con la precisión de la unidad base.
 * Los enteros se muestran sin decimales («208 unidades») y el resto conserva
 * hasta tres decimales («45,500 kg», «0,750 kg»).
 */
export function formatearCantidad(valor: EntradaDecimal, maximoDecimales = 3): string {
  const decimal = Decimal.desde(valor);
  const esEntero = decimal.redondear(0).comparar(decimal) === 0;
  if (esEntero) return conSeparadorMiles(decimal.redondear(0).aTexto(0));
  const texto = decimal.redondear(maximoDecimales).aTexto(maximoDecimales);
  const [entero, fraccion = ''] = texto.split('.');
  return `${conSeparadorMiles(entero)},${fraccion}`;
}

/** Formatea una cantidad con signo explícito (`+240 unidades`, `−750 g`). */
export function formatearCantidadConSigno(valor: EntradaDecimal, maximoDecimales = 3): string {
  const decimal = Decimal.desde(valor);
  const magnitud = formatearCantidad(decimal.esNegativo() ? decimal.multiplica(-1) : decimal, maximoDecimales);
  if (decimal.esCero()) return magnitud;
  return `${decimal.esNegativo() ? '−' : '+'}${magnitud}`;
}

/** Traduce el nombre de la unidad base del backend a una unidad legible. */
const UNIDADES: Record<
  string,
  { factor: string; singular: string; plural: string; etiqueta: string; etiquetaGrande: string }
> = {
  unidad: {
    factor: '1',
    singular: 'unidad',
    plural: 'unidades',
    etiqueta: 'und',
    etiquetaGrande: 'und',
  },
  gramo: {
    factor: '0.001',
    singular: 'gramo',
    plural: 'gramos',
    etiqueta: 'g',
    etiquetaGrande: 'kg',
  },
  mililitro: {
    factor: '0.001',
    singular: 'mililitro',
    plural: 'mililitros',
    etiqueta: 'ml',
    etiquetaGrande: 'L',
  },
  kilogramo: {
    factor: '1',
    singular: 'kilogramo',
    plural: 'kilogramos',
    etiqueta: 'kg',
    etiquetaGrande: 'kg',
  },
  litro: {
    factor: '1',
    singular: 'litro',
    plural: 'litros',
    etiqueta: 'L',
    etiquetaGrande: 'L',
  },
};

/**
 * Expresa una cantidad base en la unidad que el usuario entiende.
 * Ejemplos: `45 500 g` → «45,500 kg»; `2 000` unidades → «2 unidades».
 */
export function formatearEnUnidadLegible(
  cantidad: EntradaDecimal,
  unidadBase: string | null | undefined,
): string {
  const decimal = Decimal.desde(cantidad);
  if (!unidadBase) return formatearCantidad(decimal);

  const clave = unidadBase.trim().toLowerCase();
  const unidad = UNIDADES[clave];
  if (!unidad) return `${formatearCantidad(decimal)} ${unidadBase.toLowerCase()}`;

  const negativo = decimal.esNegativo();
  const magnitud = negativo ? decimal.multiplica(-1) : decimal;

  if (unidad.factor === '1') {
    const texto = formatearCantidad(magnitud);
    const plural = texto === '1' ? unidad.singular : unidad.plural;
    return `${negativo ? '−' : ''}${texto} ${plural}`;
  }

  // Peso y volumen: se promueve a kg o L cuando la cantidad alcanza el múltiplo.
  if (magnitud.comparar('1000') >= 0) {
    const convertido = magnitud.multiplica(unidad.factor);
    return `${negativo ? '−' : ''}${formatearCantidad(convertido, 3)} ${unidad.etiquetaGrande}`;
  }

  return `${negativo ? '−' : ''}${formatearCantidad(magnitud, 0)} ${unidad.etiqueta}`;
}

/** Etiqueta corta de unidad para encabezados de tabla. */
export function abreviarUnidad(unidadBase: string | null | undefined): string {
  if (!unidadBase) return 'und';
  const clave = unidadBase.trim().toLowerCase();
  return UNIDADES[clave]?.etiqueta ?? unidadBase.toLowerCase();
}

/**
 * Expresa una cantidad de presentación (sacos y medios sacos) con fracciones
 * legibles: `0.5` → «1/2 saco», `1.5` → «1 1/2 sacos», `-0.5` → «−1/2 saco».
 */
export function formatearEquivalenciaSacos(
  cantidadPresentacion: EntradaDecimal,
  nombrePresentacion?: string | null,
): string {
  const decimal = Decimal.desde(cantidadPresentacion).redondear(4);
  const negativo = decimal.esNegativo();
  const magnitud = negativo ? decimal.multiplica(-1) : decimal;
  const signo = negativo ? '−' : '';

  const [enteroTexto] = magnitud.aTexto(4).split('.');
  const entero = Decimal.desde(enteroTexto || '0');
  const resto = magnitud.resta(entero);

  let cantidadTexto: string;
  if (magnitud.esCero()) {
    cantidadTexto = '0';
  } else if (resto.esCero()) {
    cantidadTexto = conSeparadorMiles(entero.aTexto(0));
  } else if (resto.comparar('0.5') === 0) {
    cantidadTexto = entero.esCero()
      ? '1/2'
      : `${conSeparadorMiles(entero.aTexto(0))} 1/2`;
  } else {
    cantidadTexto = formatearCantidad(magnitud, 3);
  }

  const etiqueta = (nombrePresentacion ?? '').trim();
  if (etiqueta) {
    return `${signo}${cantidadTexto} ${etiqueta}`;
  }
  const singular = !magnitud.esCero() && magnitud.comparar('1') <= 0;
  return `${signo}${cantidadTexto} ${singular ? 'saco' : 'sacos'}`;
}

/**
 * Convierte una cantidad en unidad base (p. ej. gramos) a la presentación del
 * lote (p. ej. sacos y medios sacos) cuando el factor es mayor que 1.
 */
export function formatearStockEnPresentacion(
  cantidadBase: EntradaDecimal,
  factorBase?: EntradaDecimal,
  nombrePresentacion?: string | null,
  unidadBase?: string | null,
): { principal: string; secundario: string | null } {
  const base = Decimal.desde(cantidadBase);
  const factor = Decimal.desde(factorBase ?? '1');
  if (factor.comparar('1') > 0) {
    const enPresentacion = base.divide(factor, 4);
    return {
      principal: formatearEquivalenciaSacos(enPresentacion, nombrePresentacion),
      secundario: formatearEnUnidadLegible(base, unidadBase),
    };
  }
  if (nombrePresentacion) {
    return {
      principal: `${formatearCantidad(base)} ${nombrePresentacion}`,
      secundario: unidadBase ? formatearEnUnidadLegible(base, unidadBase) : null,
    };
  }
  return {
    principal: formatearEnUnidadLegible(base, unidadBase),
    secundario: null,
  };
}

const FECHA_LARGA = new Intl.DateTimeFormat('es-PE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const FECHA_HORA = new Intl.DateTimeFormat('es-PE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

const HORA = new Intl.DateTimeFormat('es-PE', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

/** Convierte a `Date` aceptando fechas ISO (`2026-11-08`) o marcas de tiempo. */
function aFecha(valor: string | null | undefined): Date | null {
  if (!valor) return null;
  const fecha = new Date(valor.length === 10 ? `${valor}T00:00:00` : valor);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

/** Fecha en formato local peruano: `08/11/2026`. */
export function formatearFecha(valor: string | null | undefined): string {
  const fecha = aFecha(valor);
  return fecha ? FECHA_LARGA.format(fecha) : '—';
}

/** Fecha y hora en formato local peruano: `08/11/2026 16:42`. */
export function formatearFechaHora(valor: string | null | undefined): string {
  const fecha = aFecha(valor);
  return fecha ? FECHA_HORA.format(fecha) : '—';
}

/** Solo la hora: `16:42`. */
export function formatearHora(valor: string | null | undefined): string {
  const fecha = aFecha(valor);
  return fecha ? HORA.format(fecha) : '—';
}

/** Fecha de hoy en ISO (`aaaa-mm-dd`), para los filtros por periodo. */
export function hoyISO(): string {
  const ahora = new Date();
  const mes = String(ahora.getMonth() + 1).padStart(2, '0');
  const dia = String(ahora.getDate()).padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

/** Primer día del mes actual en ISO (`aaaa-mm-dd`). */
export function inicioMesISO(): string {
  const ahora = new Date();
  const mes = String(ahora.getMonth() + 1).padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-01`;
}

/** Fecha de hace cierta cantidad de días en ISO (`aaaa-mm-dd`). */
export function haceDiasISO(dias: number): string {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - dias);
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

/** Formatea un porcentaje: `12,34 %`. */
export function formatearPorcentaje(valor: EntradaDecimal, decimales = 2): string {
  return `${formatearNumero(valor, decimales)} %`;
}

/** Etiqueta legible del estado de existencias (el color nunca va solo). */
export function etiquetaEstado(estado: string | null | undefined): string {
  switch (estado) {
    case 'agotado':
      return 'Agotado';
    case 'bajo_minimo':
      return 'Bajo mínimo';
    case 'disponible':
      return 'Disponible';
    default:
      return 'Sin estado';
  }
}

/** Etiqueta legible del tipo de movimiento del kardex. */
export function etiquetaTipoMovimiento(tipo: string | null | undefined): string {
  switch (tipo) {
    case 'SALDO_INICIAL':
      return 'Saldo inicial';
    case 'ABASTECIMIENTO':
      return 'Ingreso';
    case 'VENTA':
      return 'Venta';
    case 'REVERSO_VENTA':
      return 'Anulación de venta';
    case 'REVERSO_ABASTECIMIENTO':
      return 'Anulación de ingreso';
    case 'AJUSTE_ADMINISTRATIVO':
      return 'Ajuste';
    default:
      return tipo ?? 'Movimiento';
  }
}

/** Etiqueta legible del estado de una operación. */
export function etiquetaEstadoOperacion(estado: string | null | undefined): string {
  switch (estado) {
    case 'CONFIRMADO':
      return 'Confirmado';
    case 'ANULADO':
      return 'Anulado';
    case 'BORRADOR':
      return 'Borrador';
    default:
      return estado ?? '—';
  }
}
