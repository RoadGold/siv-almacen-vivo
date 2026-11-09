import type { ReactNode } from 'react';

export type TonoBadge = 'neutro' | 'marca' | 'acento' | 'aviso' | 'peligro' | 'contorno';

export interface BadgeProps {
  children: ReactNode;
  tono?: TonoBadge;
  className?: string;
  titulo?: string;
}

const TONOS: Record<TonoBadge, string> = {
  neutro: 'bg-muted-tenue text-ink-suave border-linea',
  marca: 'bg-brand-tenue text-brand border-brand',
  acento: 'bg-accent-tenue text-ink border-linea-fuerte',
  aviso: 'bg-warning-tenue text-warning border-warning',
  peligro: 'bg-danger-tenue text-danger border-danger',
  contorno: 'bg-surface text-muted border-linea-fuerte',
};

/**
 * Etiqueta de estado. El color nunca es la única señal:
 * el texto del estado ("Agotado", "Bajo", "Disponible") siempre acompaña.
 */
export function Badge({ children, tono = 'neutro', className = '', titulo }: BadgeProps) {
  return (
    <span
      title={titulo}
      className={[
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide',
        TONOS[tono],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </span>
  );
}
