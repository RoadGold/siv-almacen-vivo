import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';

export type TonoToast = 'exito' | 'error' | 'info';

export interface Toast {
  id: number;
  mensaje: string;
  tono: TonoToast;
}

interface ContextoToast {
  notificar: (mensaje: string, tono?: TonoToast) => void;
}

const Contexto = createContext<ContextoToast | null>(null);

const ESTILOS: Record<TonoToast, { borde: string; texto: string; etiqueta: string }> = {
  exito: { borde: 'border-brand bg-brand-tenue', texto: 'text-ink', etiqueta: 'Listo' },
  error: { borde: 'border-danger bg-danger-tenue', texto: 'text-ink', etiqueta: 'Problema' },
  info: { borde: 'border-linea-fuerte bg-surface', texto: 'text-ink', etiqueta: 'Aviso' },
};

let contador = 0;

/** Proveedor de notificaciones breves (región «aria-live»). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notificar = useCallback((mensaje: string, tono: TonoToast = 'info') => {
    contador += 1;
    const id = contador;
    setToasts((previos) => [...previos, { id, mensaje, tono }]);
    window.setTimeout(() => {
      setToasts((previos) => previos.filter((item) => item.id !== id));
    }, 6000);
  }, []);

  const valor = useMemo(() => ({ notificar }), [notificar]);

  return (
    <Contexto.Provider value={valor}>
      {children}
      {createPortal(
        <div
          aria-live="polite"
          aria-atomic="false"
          className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2"
        >
          {toasts.map((toast) => {
            const estilo = ESTILOS[toast.tono];
            return (
              <div
                key={toast.id}
                className={[
                  'pointer-events-auto rounded-[6px] border px-4 py-3 text-sm shadow-elevado',
                  estilo.borde,
                  estilo.texto,
                ].join(' ')}
              >
                <p className="etiqueta">{estilo.etiqueta}</p>
                <p className="mt-1 leading-relaxed">{toast.mensaje}</p>
              </div>
            );
          })}
        </div>,
        document.body,
      )}
    </Contexto.Provider>
  );
}

/** Acceso a las notificaciones breves. */
export function useToast(): ContextoToast {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error('useToast debe usarse dentro de ToastProvider.');
  }
  return contexto;
}
