/**
 * Proveedor del tema visual. Envuelve la aplicación y expone la preferencia
 * (claro, oscuro o según el sistema) junto con la función para cambiarla.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  aplicarTema,
  guardarPreferencia,
  preferenciaGuardada,
  resolverTema,
  sistemaPrefiereOscuro,
  type PreferenciaTema,
  type Tema,
} from './tema';

interface ContextoTema {
  tema: Tema;
  preferencia: PreferenciaTema;
  setPreferencia: (preferencia: PreferenciaTema) => void;
  alternar: () => void;
}

const Contexto = createContext<ContextoTema | null>(null);

export function ProveedorTema({ children }: { children: ReactNode }) {
  const [preferencia, setEstadoPreferencia] = useState<PreferenciaTema>(() =>
    preferenciaGuardada(),
  );
  const [sistemaOscuro, setSistemaOscuro] = useState<boolean>(() => sistemaPrefiereOscuro());

  // Si la preferencia es «según el sistema», se sigue el cambio del sistema operativo.
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const consulta = window.matchMedia('(prefers-color-scheme: dark)');
    const alCambiar = (evento: MediaQueryListEvent) => setSistemaOscuro(evento.matches);
    consulta.addEventListener('change', alCambiar);
    return () => consulta.removeEventListener('change', alCambiar);
  }, []);

  const tema = preferencia === 'sistema' ? (sistemaOscuro ? 'oscuro' : 'claro') : preferencia;

  useEffect(() => {
    aplicarTema(tema);
  }, [tema]);

  const setPreferencia = useCallback((nueva: PreferenciaTema) => {
    setEstadoPreferencia(nueva);
    guardarPreferencia(nueva);
  }, []);

  const alternar = useCallback(() => {
    setEstadoPreferencia((actual) => {
      const temaActual = actual === 'sistema' ? resolverTema('sistema') : actual;
      const nueva: PreferenciaTema = temaActual === 'oscuro' ? 'claro' : 'oscuro';
      guardarPreferencia(nueva);
      return nueva;
    });
  }, []);

  const valor = useMemo(
    () => ({ tema, preferencia, setPreferencia, alternar }),
    [tema, preferencia, setPreferencia, alternar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useTema(): ContextoTema {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error('useTema debe usarse dentro de <ProveedorTema>.');
  }
  return contexto;
}
