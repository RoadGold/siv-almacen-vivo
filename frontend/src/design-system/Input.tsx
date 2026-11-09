import { forwardRef, type InputHTMLAttributes } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Texto de ayuda mostrado bajo el campo. */
  ayuda?: string;
  /** Marca el campo como inválido (el texto de error se anuncia). */
  invalido?: boolean;
  /** Prefijo visual fijo (por ejemplo «S/»). */
  prefijo?: string;
}

/** Campo de texto del sistema visual. */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { ayuda, invalido = false, prefijo, className = '', id, ...resto },
  ref,
) {
  const clasesControl = [
    'w-full rounded-[6px] border bg-surface px-3 py-2 text-sm text-ink placeholder:text-muted',
    'transition-colors focus:border-brand',
    invalido ? 'border-danger' : 'border-linea-fuerte',
    prefijo ? 'pl-9' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="w-full">
      {prefijo ? (
        <div className="relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">
            {prefijo}
          </span>
          <input
            ref={ref}
            id={id}
            aria-invalid={invalido || undefined}
            className={clasesControl}
            {...resto}
          />
        </div>
      ) : (
        <input
          ref={ref}
          id={id}
          aria-invalid={invalido || undefined}
          className={clasesControl}
          {...resto}
        />
      )}
      {ayuda ? (
        <p className="mt-1 text-xs text-muted">{ayuda}</p>
      ) : null}
    </div>
  );
});
