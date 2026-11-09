import { useCallback, useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

export interface ModalProps {
  abierto: boolean;
  titulo: string;
  descripcion?: string;
  onCerrar: () => void;
  children: ReactNode;
  /** Contenido de la barra inferior (acciones). */
  pie?: ReactNode;
  ancho?: 'md' | 'lg' | 'xl';
}

const ANCHOS: Record<'md' | 'lg' | 'xl', string> = {
  md: 'max-w-lg',
  lg: 'max-w-3xl',
  xl: 'max-w-5xl',
};

/**
 * Modal accesible: foco atrapado, cierre con Escape, devolución del foco
 * al elemento que lo abrió y bloqueo del scroll de fondo.
 */
export function Modal({
  abierto,
  titulo,
  descripcion,
  onCerrar,
  children,
  pie,
  ancho = 'md',
}: ModalProps) {
  const contenedorRef = useRef<HTMLDivElement>(null);
  const focoPrevio = useRef<HTMLElement | null>(null);
  const tituloId = useRef(`titulo-modal-${Math.random().toString(36).slice(2)}`);

  const manejarTecla = useCallback(
    (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') {
        evento.stopPropagation();
        onCerrar();
        return;
      }
      if (evento.key !== 'Tab') return;

      const contenedor = contenedorRef.current;
      if (!contenedor) return;

      const focusables = Array.from(
        contenedor.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((elemento) => elemento.offsetParent !== null || elemento === document.activeElement);

      if (focusables.length === 0) {
        evento.preventDefault();
        return;
      }

      const primero = focusables[0];
      const ultimo = focusables[focusables.length - 1];
      const activo = document.activeElement as HTMLElement | null;

      if (evento.shiftKey && (activo === primero || !contenedor.contains(activo))) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && activo === ultimo) {
        evento.preventDefault();
        primero.focus();
      }
    },
    [onCerrar],
  );

  useEffect(() => {
    if (!abierto) return undefined;

    focoPrevio.current = document.activeElement as HTMLElement | null;
    const scrollAnterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', manejarTecla, true);

    const temporizador = window.setTimeout(() => {
      const contenedor = contenedorRef.current;
      const primerFoco = contenedor?.querySelector<HTMLElement>(
        'input:not([type="hidden"]), select, textarea, button',
      );
      (primerFoco ?? contenedor)?.focus();
    }, 20);

    return () => {
      window.clearTimeout(temporizador);
      document.removeEventListener('keydown', manejarTecla, true);
      document.body.style.overflow = scrollAnterior;
      focoPrevio.current?.focus?.();
    };
  }, [abierto, manejarTecla]);

  if (!abierto) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-overlay p-4 sm:p-8">
      <div
        className="absolute inset-0"
        aria-hidden="true"
        onClick={onCerrar}
        data-prueba="fondo-modal"
      />
      <div
        ref={contenedorRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={tituloId.current}
        tabIndex={-1}
        className={[
          'relative z-10 w-full rounded-tarjeta border border-linea bg-surface shadow-elevado',
          ANCHOS[ancho],
        ].join(' ')}
      >
        <header className="flex items-start justify-between gap-4 border-b border-linea px-5 py-4">
          <div>
            <h2 id={tituloId.current} className="text-lg font-semibold text-ink">
              {titulo}
            </h2>
            {descripcion ? <p className="mt-1 text-sm text-muted">{descripcion}</p> : null}
          </div>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar ventana"
            className="rounded-[6px] border border-linea px-2 py-1 text-sm text-muted hover:border-brand hover:text-brand"
          >
            ✕
          </button>
        </header>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {pie ? (
          <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-linea bg-surface-tenue px-5 py-3">
            {pie}
          </footer>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
