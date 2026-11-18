/**
 * Reglas de validación del cliente.
 *
 * Estas reglas **no se escriben a mano**: se extraen de los schemas del
 * backend y se guardan en `reglas.json` (que genera
 * `python -m app.core.contrato_cli --escribir`). Así el cliente aplica la
 * misma regla que el servidor, y el test `reglas.test.ts` falla si alguien
 * cambia una regla en el backend y no se regenera el archivo.
 *
 * El backend sigue siendo la autoridad: estas reglas solo sirven para avisar
 * antes de enviar, sin una ida y vuelta al servidor.
 */

import reglas from './reglas.json';

export interface ReglaCampo {
  /** Longitud mínima (caracteres). */
  min?: number;
  /** Longitud máxima (caracteres). */
  max?: number;
  /** El número debe ser mayor que este valor. */
  mayor?: number;
  /** El número debe ser menor o igual que este valor. */
  menor_igual?: number;
  /** El número debe ser mayor o igual que este valor. */
  mayor_igual?: number;
}

export type ReglasGrupo = Record<string, ReglaCampo>;

/** Todas las reglas por grupo. */
export const REGLAS = reglas.reglas as unknown as Record<string, ReglasGrupo>;

/** Formas de pago que admite la caja. */
export const FORMAS_PAGO: string[] = reglas.formas_pago;

/** Reglas de un grupo. Si el grupo no existe, no hay reglas. */
export function reglasDe(grupo: string): ReglasGrupo {
  return REGLAS[grupo] ?? {};
}

/** Regla de un campo dentro de un grupo. */
export function reglaDe(grupo: string, campo: string): ReglaCampo {
  return reglasDe(grupo)[campo] ?? {};
}

/* --- Reglas que no son de longitud ni de número ------------------------- */

/** Un RUC peruano tiene 11 dígitos. */
export const REGLAS_RUC = /^\d{11}$/;

/** Un correo electrónico tiene la forma de un correo. */
export const REGLAS_EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/* --- Mensajes ------------------------------------------------------------ */

/**
 * Texto del aviso cuando un texto no cumple la longitud del campo.
 * Devuelve `undefined` si el texto sí cumple.
 */
export function errorDeLongitud(
  valor: string,
  regla: ReglaCampo,
  nombre: string,
): string | undefined {
  const largo = valor.trim().length;
  if (regla.min !== undefined && largo < regla.min) {
    return `«${nombre}» debe tener al menos ${regla.min} caracteres.`;
  }
  if (regla.max !== undefined && largo > regla.max) {
    return `«${nombre}» no puede pasar de ${regla.max} caracteres.`;
  }
  return undefined;
}
