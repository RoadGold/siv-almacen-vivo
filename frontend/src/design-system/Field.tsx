import type { ReactNode } from 'react';

export interface FieldProps {
  /** Identificador del control (se enlaza con `htmlFor`). */
  htmlFor: string;
  etiqueta: string;
  children: ReactNode;
  /** Texto de ayuda o de error. */
  ayuda?: string;
  error?: string;
  obligatorio?: boolean;
  className?: string;
}

/**
 * Envoltorio de campo: etiqueta, control, ayuda y error.
 * El error se anuncia con `role="alert"` y el control debe usar `invalido`.
 */
export function Field({
  htmlFor,
  etiqueta,
  children,
  ayuda,
  error,
  obligatorio = false,
  className = '',
}: FieldProps) {
  return (
    <div className={['flex flex-col gap-1.5', className].filter(Boolean).join(' ')}>
      <label htmlFor={htmlFor} className="text-sm font-semibold text-ink">
        {etiqueta}
        {obligatorio ? (
          <span className="ml-1 text-danger" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {children}
      {error ? (
        <p role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      ) : ayuda ? (
        <p className="text-xs text-muted">{ayuda}</p>
      ) : null}
    </div>
  );
}
