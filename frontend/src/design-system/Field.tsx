import { cloneElement, isValidElement, type ReactNode } from 'react';
import { Select } from './Select';

export interface FieldProps {
  /** Identificador del control (se enlaza con `htmlFor`). */
  htmlFor: string;
  /** Nombre del dato que se debe rellenar. Siempre visible. */
  etiqueta: string;
  children: ReactNode;
  /** Texto de ayuda o de error. */
  ayuda?: string;
  /** Ejemplo de lo que se debe escribir (se muestra dentro del cuadro). */
  ejemplo?: string;
  error?: string;
  obligatorio?: boolean;
  className?: string;
  /** Etiqueta pequeña, para las filas densas (carrito, recepción). */
  compacto?: boolean;
}

/**
 * Envoltorio de campo: nombre visible del dato, ejemplo de lo que se escribe,
 * ayuda y error.
 *
 * El ejemplo se aplica automáticamente como `placeholder` del control, para que
 * ningún campo del sistema quede sin la pista de qué se debe escribir.
 */
export function Field({
  htmlFor,
  etiqueta,
  children,
  ayuda,
  ejemplo,
  error,
  obligatorio = false,
  className = '',
  compacto = false,
}: FieldProps) {
  // El placeholder solo tiene sentido en los cuadros de texto.
  const control =
    ejemplo && isValidElement(children) && children.type !== Select
      ? cloneElement(children as React.ReactElement<{ placeholder?: string }>, {
          placeholder: ejemplo,
        })
      : children;

  return (
    <div className={['flex flex-col gap-1.5', className].filter(Boolean).join(' ')}>
      <label
        htmlFor={htmlFor}
        className={
          compacto
            ? 'etiqueta'
            : 'text-sm font-semibold text-ink'
        }
      >
        {etiqueta}
        {obligatorio ? (
          <span className="ml-1 text-danger" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {control}
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
