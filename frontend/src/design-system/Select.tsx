import { forwardRef, type SelectHTMLAttributes } from 'react';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalido?: boolean;
  ayuda?: string;
}

/** Lista desplegable del sistema visual. */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalido = false, ayuda, className = '', children, id, ...resto },
  ref,
) {
  return (
    <div className="w-full">
      <select
        ref={ref}
        id={id}
        aria-invalid={invalido || undefined}
        className={[
          'w-full rounded-[6px] border bg-surface px-3 py-2 text-sm text-ink',
          'focus:border-brand',
          invalido ? 'border-danger' : 'border-linea-fuerte',
          className,
        ]
          .filter(Boolean)
          .join(' ')}
        {...resto}
      >
        {children}
      </select>
      {ayuda ? <p className="mt-1 text-xs text-muted">{ayuda}</p> : null}
    </div>
  );
});
