/**
 * Registro de la última operación realizada en la aplicación.
 * Alimenta la «barra de pulso» (plan §2.2, elemento de marca 1).
 */

export interface Operacion {
  descripcion: string;
  /** Marca de tiempo ISO del momento en que se registró. */
  momento: string;
}

type Escucha = (operacion: Operacion | null) => void;

let operacionActual: Operacion | null = null;
const escuchas = new Set<Escucha>();

/** Registra la última operación confirmada (venta, ingreso, alta, etc.). */
export function registrarOperacion(descripcion: string): void {
  operacionActual = { descripcion, momento: new Date().toISOString() };
  escuchas.forEach((escucha) => escucha(operacionActual));
}

/** Última operación registrada. */
export function obtenerOperacion(): Operacion | null {
  return operacionActual;
}

/** Se suscribe a los cambios de la última operación. */
export function suscribirOperacion(escucha: Escucha): () => void {
  escuchas.add(escucha);
  escucha(operacionActual);
  return () => {
    escuchas.delete(escucha);
  };
}
