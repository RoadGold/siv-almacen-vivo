export interface SpinnerProps {
  /** Texto accesible que describe la operación en curso. */
  etiqueta?: string;
  tamano?: 'sm' | 'md';
  className?: string;
}

/** Indicador de carga con texto visible (el estado no depende solo del color). */
export function Spinner({ etiqueta = 'Cargando…', tamano = 'md', className = '' }: SpinnerProps) {
  const dimension = tamano === 'sm' ? 'h-4 w-4' : 'h-6 w-6';
  return (
    <div
      role="status"
      aria-live="polite"
      className={['flex items-center gap-2 text-sm text-muted', className].filter(Boolean).join(' ')}
    >
      <span
        aria-hidden="true"
        className={`${dimension} animate-spin rounded-full border-2 border-linea-fuerte border-t-brand`}
      />
      <span>{etiqueta}</span>
    </div>
  );
}

/** Bloque de carga para paneles completos. */
export function LoadingBlock({ etiqueta = 'Cargando…' }: { etiqueta?: string }) {
  return (
    <div className="flex min-h-[120px] items-center justify-center px-4 py-8">
      <Spinner etiqueta={etiqueta} />
    </div>
  );
}
