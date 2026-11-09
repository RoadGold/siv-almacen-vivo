/**
 * Almacén de sesión en el navegador.
 * El token y los datos del usuario se guardan en `localStorage` para que la
 * aplicación sobreviva a una recarga del navegador (uso local, una sola máquina).
 */

export interface UsuarioSesion {
  id: number;
  nombre: string;
  usuario: string;
  activo: boolean;
  roles: string[];
  permisos: string[];
}

const CLAVE_TOKEN = 'siv.token';
const CLAVE_USUARIO = 'siv.usuario';

type Escucha = (token: string | null, usuario: UsuarioSesion | null) => void;

const escuchas = new Set<Escucha>();

function leerToken(): string | null {
  try {
    return window.localStorage.getItem(CLAVE_TOKEN);
  } catch {
    return null;
  }
}

function leerUsuario(): UsuarioSesion | null {
  try {
    const texto = window.localStorage.getItem(CLAVE_USUARIO);
    if (!texto) return null;
    return JSON.parse(texto) as UsuarioSesion;
  } catch {
    return null;
  }
}

/** Token de acceso vigente (o `null` si la sesión no está iniciada). */
export function obtenerToken(): string | null {
  return leerToken();
}

/** Datos del usuario de la sesión vigente. */
export function obtenerUsuario(): UsuarioSesion | null {
  return leerUsuario();
}

/** Guarda token y usuario, y notifica a los suscriptores. */
export function guardarSesion(token: string, usuario: UsuarioSesion): void {
  try {
    window.localStorage.setItem(CLAVE_TOKEN, token);
    window.localStorage.setItem(CLAVE_USUARIO, JSON.stringify(usuario));
  } catch {
    /* almacenamiento no disponible: la sesión durará lo que la página */
  }
  notificarCambio();
}

/** Cierra la sesión en el navegador y notifica el cambio. */
export function cerrarSesion(): void {
  try {
    window.localStorage.removeItem(CLAVE_TOKEN);
    window.localStorage.removeItem(CLAVE_USUARIO);
  } catch {
    /* sin almacenamiento disponible */
  }
  notificarCambio();
}

/** Indica si el usuario tiene el permiso indicado. */
export function tienePermiso(permiso: string, usuario?: UsuarioSesion | null): boolean {
  const actual = usuario ?? leerUsuario();
  if (!actual) return false;
  return actual.permisos.includes(permiso);
}

/** Se suscribe a los cambios de sesión. Devuelve la función para cancelar. */
export function suscribirSesion(escucha: Escucha): () => void {
  escuchas.add(escucha);
  return () => {
    escuchas.delete(escucha);
  };
}

function notificarCambio(): void {
  const token = leerToken();
  const usuario = leerUsuario();
  escuchas.forEach((escucha) => escucha(token, usuario));
}

/** Controladores que deben actuar cuando el servidor responde 401. */
type ControladorSesionExpirada = () => void;

const controladores = new Set<ControladorSesionExpirada>();

/** Registra el manejador global de «sesión expirada». */
export function registrarControladorSesionExpirada(controlador: ControladorSesionExpirada): () => void {
  controladores.add(controlador);
  return () => {
    controladores.delete(controlador);
  };
}

/** Avisa a toda la aplicación de que el servidor rechazó el token. */
export function notificarSesionExpirada(): void {
  cerrarSesion();
  controladores.forEach((controlador) => controlador());
}
