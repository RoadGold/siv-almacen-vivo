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

/** Un error de validación tal como lo manda el backend. */
interface DetalleCampo {
  loc?: unknown[];
  msg?: string;
}

/**
 * Extrae los errores por campo de una respuesta de validación.
 *
 * El backend responde `{ error: { codigo, mensaje, detalle: { campos: [...] } } }`,
 * y cada entrada de `campos` dice qué campo falló (`loc`) y por qué (`msg`).
 * Con esto el aviso aterriza **bajo el campo** que hay que corregir, en vez de
 * aparecer suelto en un aviso general.
 *
 * Devuelve un mapa `{ nombreDelCampo: mensaje }`; vacío si no hay detalle.
 */
export function erroresPorCampo(error: unknown): Record<string, string> {
  if (!(error instanceof ErrorApi)) return {};
  const campos = error.detalle?.campos;
  if (!Array.isArray(campos)) return {};

  const errores: Record<string, string> = {};
  for (const item of campos as DetalleCampo[]) {
    const ruta = Array.isArray(item.loc) ? item.loc : [];
    // Se toma el último tramo: en una línea del carrito el campo es
    // «lineas → 0 → cantidad», y lo que importa es «cantidad».
    const campo = String(ruta[ruta.length - 1] ?? '');
    const mensaje = String(item.msg ?? 'valor no válido');
    if (!campo) continue;
    if (!errores[campo]) errores[campo] = mensaje;
  }
  return errores;
}

/**
 * Mensaje de un error de campo, listo para mostrar bajo el control.
 * Si el backend no.detailó el campo, devuelve el mensaje general.
 */
export function mensajeDeCampo(error: unknown, campo: string): string | undefined {
  const errores = erroresPorCampo(error);
  return errores[campo];
}
