import { Notice } from './Notice';
import { erroresPorCampo } from '../shared/hooks/errores';

export interface AvisoErroresProps {
  /** Error capturado de la API. */
  error: unknown;
  /** Texto del encabezado. */
  titulo?: string;
  className?: string;
}

/**
 * Aviso que muestra **qué campo** hay que corregir.
 *
 * El backend responde con el detalle de cada campo que falló; este aviso lo
 * traduce a una lista legible, para que la persona sepa dónde mirar en vez de
 * leer un mensaje suelto.
 */
export function AvisoErrores({ error, titulo, className = '' }: AvisoErroresProps) {
  const errores = erroresPorCampo(error);
  const entradas = Object.entries(errores);

  if (entradas.length === 0) {
    // No hay detalle por campo: se muestra el mensaje general.
    const general =
      error instanceof Error && error.message ? error.message : 'Revisa los datos enviados.';
    return (
      <Notice tono="error" titulo={titulo} className={className}>
        {general}
      </Notice>
    );
  }

  return (
    <Notice tono="error" titulo={titulo} className={className}>
      <ul className="list-disc pl-5">
        {entradas.map(([campo, mensaje]) => (
          <li key={campo}>
            <span className="font-semibold">{campo}</span>: {mensaje}
          </li>
        ))}
      </ul>
    </Notice>
  );
}
