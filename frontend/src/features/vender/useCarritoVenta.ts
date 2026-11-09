import { useCallback, useMemo, useState } from 'react';
import { Decimal } from '@/shared/format/decimal';
import type { LineaCarrito } from './tipos';

/**
 * Carrito de venta editable.
 * Todos los importes se calculan con aritmética decimal exacta.
 */
export function useCarritoVenta() {
  const [lineas, setLineas] = useState<LineaCarrito[]>([]);

  const agregar = useCallback((linea: LineaCarrito) => {
    setLineas((actuales) => {
      const existente = actuales.find(
        (item) =>
          item.producto_id === linea.producto_id &&
          item.presentacion_id === linea.presentacion_id,
      );
      if (!existente) return [...actuales, linea];
      const cantidadTotal = Decimal.desde(existente.cantidad).suma(linea.cantidad);
      return actuales.map((item) =>
        item.id === existente.id ? { ...item, cantidad: cantidadTotal.aTexto() } : item,
      );
    });
  }, []);

  const quitar = useCallback((id: string) => {
    setLineas((actuales) => actuales.filter((item) => item.id !== id));
  }, []);

  const cambiarCantidad = useCallback((id: string, cantidad: string) => {
    setLineas((actuales) =>
      actuales.map((item) => (item.id === id ? { ...item, cantidad } : item)),
    );
  }, []);

  const limpiar = useCallback(() => setLineas([]), []);

  const total = useMemo(
    () =>
      lineas.reduce(
        (acumulado, linea) =>
          acumulado.suma(Decimal.desde(linea.cantidad).multiplica(linea.precio_unitario)),
        Decimal.cero(),
      ),
    [lineas],
  );

  const cantidadPiezas = useMemo(
    () => lineas.reduce((acumulado, linea) => acumulado.suma(linea.cantidad), Decimal.cero()),
    [lineas],
  );

  return {
    lineas,
    agregar,
    quitar,
    cambiarCantidad,
    limpiar,
    total,
    cantidadPiezas,
    vacia: lineas.length === 0,
  };
}

/** Genera un identificador local estable para las líneas del carrito. */
export function nuevoIdLinea(): string {
  return `linea-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Genera una clave de idempotencia para el registro de la venta. */
export function generarClaveIdempotencia(): string {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi && typeof cryptoApi.randomUUID === 'function') {
    return cryptoApi.randomUUID();
  }
  return `clave-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}
