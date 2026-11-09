/**
 * Interruptor de tema visual (claro / oscuro / según el sistema).
 *
 * Control compacto con tres opciones y textos visibles: el color nunca es la
 * única señal, y cada botón tiene su etiqueta accesible.
 */

import { useTema } from '@/shared/tema/ProveedorTema';
import type { PreferenciaTema } from '@/shared/tema/tema';

const OPCIONES: { valor: PreferenciaTema; texto: string; icono: JSX.Element }[] = [
  {
    valor: 'claro',
    texto: 'Modo claro',
    icono: (
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" aria-hidden="true" fill="none">
        <circle cx="12" cy="12" r="4.2" stroke="currentColor" strokeWidth="1.8" />
        <path
          d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    valor: 'oscuro',
    texto: 'Modo oscuro',
    icono: (
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" aria-hidden="true" fill="none">
        <path
          d="M20 13.4A8.2 8.2 0 0 1 10.6 4a8.2 8.2 0 1 0 9.4 9.4Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    valor: 'sistema',
    texto: 'Según el sistema',
    icono: (
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" aria-hidden="true" fill="none">
        <rect x="3" y="4.5" width="18" height="12" rx="2" stroke="currentColor" strokeWidth="1.8" />
        <path d="M9 20h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
];

export function InterruptorTema({ compacto = true }: { compacto?: boolean }) {
  const { preferencia, setPreferencia } = useTema();

  return (
    <div
      role="group"
      aria-label="Tema visual"
      className={[
        'inline-flex items-center gap-0.5 rounded-[6px] border border-linea bg-surface p-0.5',
        compacto ? 'text-2xs' : 'text-sm',
      ].join(' ')}
    >
      {OPCIONES.map((opcion) => {
        const activo = preferencia === opcion.valor;
        return (
          <button
            key={opcion.valor}
            type="button"
            onClick={() => setPreferencia(opcion.valor)}
            aria-pressed={activo}
            title={opcion.texto}
            className={[
              'inline-flex items-center gap-1 rounded-[4px] px-2 py-1 font-semibold transition-colors',
              activo
                ? 'bg-brand text-sobre-brand'
                : 'text-muted hover:bg-surface-tenue hover:text-ink',
            ].join(' ')}
          >
            {opcion.icono}
            <span className={compacto ? 'sr-only sm:not-sr-only' : ''}>{opcion.texto}</span>
          </button>
        );
      })}
    </div>
  );
}
