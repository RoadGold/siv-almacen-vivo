/**
 * Errores de la API traducidos a mensajes para la interfaz.
 */

import { ErrorApi } from '../api/client';

/** Devuelve un mensaje legible para cualquier error capturado. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ErrorApi) return error.mensaje;
  if (error instanceof Error) return error.message;
  return 'Ocurrió un error inesperado.';
}

/** Indica si el error corresponde a falta de permisos (HTTP 403). */
export function esSinPermisos(error: unknown): boolean {
  return error instanceof ErrorApi && error.estado === 403;
}

/** Indica si el error corresponde a sesión expirada o ausente (HTTP 401). */
export function esSesionExpirada(error: unknown): boolean {
  return error instanceof ErrorApi && error.estado === 401;
}
