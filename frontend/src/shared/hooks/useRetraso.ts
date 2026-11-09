import { useEffect, useState } from 'react';

/**
 * Retrasa la propagación de un valor para no consultar el servidor en cada tecla.
 * `300 ms` es suficiente para el buscador local sin hacer sentir la espera.
 */
export function useRetraso<T>(valor: T, demora = 300): T {
  const [valorRetrasado, setValorRetrasado] = useState(valor);

  useEffect(() => {
    const temporizador = window.setTimeout(() => setValorRetrasado(valor), demora);
    return () => window.clearTimeout(temporizador);
  }, [valor, demora]);

  return valorRetrasado;
}
