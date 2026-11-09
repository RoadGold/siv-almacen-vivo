import type { ReactNode } from 'react';

export interface EmptyStateProps {
  titulo: string;
  descripcion?: string;
  accion?: ReactNode;
  /** Texto breve que explica qué hacer a continuación. */
  sugerencia?: string;
}

/** Estado vacío: nunca se muestra una tabla en blanco sin explicación. */
export function EmptyState({ titulo, descripcion, accion, sugerencia }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <div
        aria-hidden="true"
        className="flex h-11 w-11 items-center justify-center rounded-full border border-dashed border-linea-fuerte text-lg text-muted"
      >
        ∅
      </div>
      <p className="text-sm font-semibold text-ink">{titulo}</p>
      {descripcion ? <p className="max-w-md text-sm text-muted">{descripcion}</p> : null}
      {sugerencia ? <p className="text-xs text-muted">{sugerencia}</p> : null}
      {accion ? <div className="pt-2">{accion}</div> : null}
    </div>
  );
}
