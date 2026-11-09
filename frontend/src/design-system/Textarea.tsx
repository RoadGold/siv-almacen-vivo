import { forwardRef, type TextareaHTMLAttributes } from 'react';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalido?: boolean;
  ayuda?: string;
}

/** Área de texto multilínea. */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalido = false, ayuda, className = '', id, ...resto },
  ref,
) {
  return (
    <div className="w-full">
      <textarea
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
      />
      {ayuda ? <p className="mt-1 text-xs text-muted">{ayuda}</p> : null}
    </div>
  );
});
