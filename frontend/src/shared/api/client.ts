/**
 * Cliente HTTP de SIV · Almacén Vivo.
 *
 * · La URL base se configura con `VITE_API_URL` (por defecto `http://127.0.0.1:8000/api/v1`).
 * · Cada petición adjunta `Authorization: Bearer <token>` si hay sesión iniciada.
 * · Los errores del backend llegan como `{ error: { codigo, mensaje, detalle } }`
 *   y se normalizan a `ErrorApi` para que la interfaz siempre muestre un mensaje útil.
 * · Un `401` con token previo cierra la sesión y devuelve al usuario al acceso.
 */

import { notificarSesionExpirada, obtenerToken } from '../auth/authStore';
import type { EstadoServidor } from '../types/api';

const URL_API_POR_DEFECTO = 'http://127.0.0.1:8000/api/v1';

const URL_API = (import.meta.env.VITE_API_URL?.trim() || URL_API_POR_DEFECTO).replace(/\/+$/, '');

/** Endpoint de salud del servidor (vive fuera del prefijo `/api/v1`). */
export const URL_SALUD = URL_API.replace(/\/api\/v1$/, '/api/salud');

/** Error normalizado de la API. */
export class ErrorApi extends Error {
  readonly codigo: string;
  readonly mensaje: string;
  readonly detalle: Record<string, unknown>;
  readonly estado: number;

  constructor(codigo: string, mensaje: string, detalle: Record<string, unknown> = {}, estado = 0) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.codigo = codigo;
    this.mensaje = mensaje;
    this.detalle = detalle;
    this.estado = estado;
  }
}

export type Metodo = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

export interface OpcionesPeticion {
  metodo?: Metodo;
  cuerpo?: unknown;
  parametros?: Record<string, string | number | boolean | null | undefined>;
  signal?: AbortSignal;
}

function construirUrl(
  ruta: string,
  parametros?: OpcionesPeticion['parametros'],
): string {
  const base = ruta.startsWith('http') ? ruta : `${URL_API}${ruta.startsWith('/') ? ruta : `/${ruta}`}`;
  const url = new URL(base);
  if (parametros) {
    Object.entries(parametros).forEach(([clave, valor]) => {
      if (valor === undefined || valor === null || valor === '') return;
      url.searchParams.set(clave, String(valor));
    });
  }
  return url.toString();
}

function extraerError(cuerpo: unknown, estado: number): ErrorApi {
  if (cuerpo && typeof cuerpo === 'object') {
    const sobre = (cuerpo as { error?: { codigo?: string; mensaje?: string; detalle?: unknown } }).error;
    if (sobre) {
      return new ErrorApi(
        sobre.codigo ?? 'error',
        sobre.mensaje ?? 'Ocurrió un error en el servidor.',
        (sobre.detalle as Record<string, unknown>) ?? {},
        estado,
      );
    }

    // FastAPI responde `{ "detail": ... }` en algunos casos (validación y HTTPException).
    const detalle = (cuerpo as { detail?: unknown }).detail;
    if (typeof detalle === 'string') {
      return new ErrorApi('error', detalle, {}, estado);
    }
    if (Array.isArray(detalle)) {
      const campos = detalle
        .map((item) => {
          const registro = item as { loc?: unknown[]; msg?: string };
          const campo = Array.isArray(registro.loc) ? registro.loc[registro.loc.length - 1] : 'campo';
          return `${String(campo)}: ${registro.msg ?? 'valor no válido'}`;
        })
        .join(' · ');
      return new ErrorApi('validacion', `Datos no válidos. ${campos}`.trim(), { campos: detalle }, estado);
    }
  }

  const mensajes: Record<number, string> = {
    400: 'La operación no cumple las reglas del negocio.',
    401: 'La sesión no está iniciada o el token expiró.',
    403: 'No tienes permisos para realizar esta acción.',
    404: 'El registro solicitado no existe.',
    409: 'La operación entra en conflicto con los datos existentes.',
    422: 'Los datos enviados no son válidos.',
  };

  return new ErrorApi(
    `http_${estado}`,
    mensajes[estado] ?? 'Ocurrió un error inesperado.',
    {},
    estado,
  );
}

/** Ejecuta una petición contra la API y devuelve el cuerpo ya deserializado. */
export async function peticion<T>(ruta: string, opciones: OpcionesPeticion = {}): Promise<T> {
  const { metodo = 'GET', cuerpo, parametros, signal } = opciones;
  const url = construirUrl(ruta, parametros);

  const cabeceras: Record<string, string> = { Accept: 'application/json' };
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';

  const token = obtenerToken();
  if (token) cabeceras.Authorization = `Bearer ${token}`;

  let respuesta: Response;
  try {
    respuesta = await fetch(url, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal,
    });
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error;
    throw new ErrorApi(
      'sin_conexion',
      'No se pudo conectar con el servidor local. Verifique que el backend esté encendido.',
      {},
      0,
    );
  }

  if (respuesta.status === 204) return undefined as T;

  const texto = await respuesta.text();
  let datos: unknown = null;
  if (texto) {
    try {
      datos = JSON.parse(texto);
    } catch {
      datos = null;
    }
  }

  if (!respuesta.ok) {
    const error = extraerError(datos, respuesta.status);
    if (respuesta.status === 401 && token) {
      notificarSesionExpirada();
    }
    throw error;
  }

  return datos as T;
}

export const api = {
  get: <T>(ruta: string, parametros?: OpcionesPeticion['parametros'], signal?: AbortSignal) =>
    peticion<T>(ruta, { metodo: 'GET', parametros, signal }),
  post: <T>(ruta: string, cuerpo?: unknown, signal?: AbortSignal) =>
    peticion<T>(ruta, { metodo: 'POST', cuerpo, signal }),
  patch: <T>(ruta: string, cuerpo?: unknown, signal?: AbortSignal) =>
    peticion<T>(ruta, { metodo: 'PATCH', cuerpo, signal }),
  delete: <T>(ruta: string, signal?: AbortSignal) =>
    peticion<T>(ruta, { metodo: 'DELETE', signal }),
};

/** Consulta el estado del servidor (no requiere autenticación). */
export async function consultarSalud(signal?: AbortSignal): Promise<EstadoServidor> {
  const respuesta = await fetch(URL_SALUD, { signal });
  if (!respuesta.ok) {
    throw new ErrorApi('sin_conexion', 'El servidor local no responde.', {}, respuesta.status);
  }
  return (await respuesta.json()) as EstadoServidor;
}
