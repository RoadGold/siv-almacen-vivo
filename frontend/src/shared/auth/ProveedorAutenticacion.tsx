import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { authApi } from '../api/endpoints';
import {
  cerrarSesion,
  guardarSesion,
  obtenerToken,
  obtenerUsuario,
  registrarControladorSesionExpirada,
  suscribirSesion,
  type UsuarioSesion,
} from './authStore';

interface ContextoAutenticacion {
  usuario: UsuarioSesion | null;
  /** `true` mientras se verifica la sesión guardada en el navegador. */
  verificando: boolean;
  iniciarSesion: (usuario: string, clave: string) => Promise<void>;
  cerrar: () => void;
  /** `true` si el usuario tiene el permiso indicado. */
  puede: (permiso: string) => boolean;
}

const Contexto = createContext<ContextoAutenticacion | null>(null);

export function ProveedorAutenticacion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioSesion | null>(obtenerUsuario());
  const [verificando, setVerificando] = useState<boolean>(() => Boolean(obtenerToken()));

  // Sincroniza el estado con los cambios que ocurren en el almacén de sesión.
  useEffect(() => {
    return suscribirSesion((_token, usuarioActual) => {
      setUsuario(usuarioActual);
      setVerificando(false);
    });
  }, []);

  // Si el servidor responde 401, la sesión se cierra y el usuario vuelve al acceso.
  useEffect(() => {
    return registrarControladorSesionExpirada(() => {
      setUsuario(null);
      setVerificando(false);
    });
  }, []);

  // Verifica el token guardado al abrir la aplicación.
  useEffect(() => {
    const token = obtenerToken();
    if (!token) {
      setVerificando(false);
      return;
    }

    let vigente = true;
    authApi
      .yo()
      .then((datos) => {
        if (!vigente) return;
        setUsuario(datos);
      })
      .catch(() => {
        if (!vigente) return;
        cerrarSesion();
        setUsuario(null);
      })
      .finally(() => {
        if (vigente) setVerificando(false);
      });

    return () => {
      vigente = false;
    };
  }, []);

  const iniciarSesion = useCallback(async (nombreUsuario: string, clave: string) => {
    const respuesta = await authApi.entrar(nombreUsuario, clave);
    guardarSesion(respuesta.access_token, respuesta.usuario);
    setUsuario(respuesta.usuario);
  }, []);

  const cerrar = useCallback(() => {
    cerrarSesion();
    setUsuario(null);
  }, []);

  const puede = useCallback(
    (permiso: string) => (usuario ? usuario.permisos.includes(permiso) : false),
    [usuario],
  );

  const valor = useMemo<ContextoAutenticacion>(
    () => ({ usuario, verificando, iniciarSesion, cerrar, puede }),
    [usuario, verificando, iniciarSesion, cerrar, puede],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

/** Acceso al estado de autenticación. */
export function useAutenticacion(): ContextoAutenticacion {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error('useAutenticacion debe usarse dentro de ProveedorAutenticacion.');
  }
  return contexto;
}
