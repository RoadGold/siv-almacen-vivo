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
          item.presentacion_id === linea.presentacion_id &&
          (item.lote_id ?? null) === (linea.lote_id ?? null) &&
          item.precio_total === linea.precio_total,
      );
      if (!existente) return [...actuales, linea];
      const cantidadTotal = Decimal.desde(existente.cantidad).suma(linea.cantidad);
      // Al unir dos líneas, el total vuelve al de lista (la cantidad cambió).
      const totalDeLista = cantidadTotal.multiplica(linea.precio_original);
      return actuales.map((item) =>
        item.id === existente.id
          ? {
              ...item,
              cantidad: cantidadTotal.aTexto(),
              precio_total: totalDeLista.redondear(2).aTexto(),
              precio_total_original: totalDeLista.redondear(2).aTexto(),
            }
          : item,
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

  /** Cambia el TOTAL de la línea (lo que se edita en la caja). */
  const cambiarPrecio = useCallback((id: string, precioTotal: string) => {
    setLineas((actuales) =>
      actuales.map((item) => (item.id === id ? { ...item, precio_total: precioTotal } : item)),
    );
  }, []);

  /** Guarda el motivo del cambio de precio (opcional). */
  const cambiarMotivo = useCallback((id: string, motivo: string) => {
    setLineas((actuales) =>
      actuales.map((item) => (item.id === id ? { ...item, motivo_precio: motivo } : item)),
    );
  }, []);

  /** Líneas cuyo total difiere del total de lista. */
  const lineasConDescuento = useMemo(
    () =>
      lineas.filter(
        (linea) => Decimal.desde(linea.precio_total).comparar(linea.precio_total_original) !== 0,
      ),
    [lineas],
  );

  /** Total a cobrar: suma de los totales de las líneas. */
  const total = useMemo(
    () =>
      lineas.reduce(
        (acumulado, linea) => acumulado.suma(Decimal.desde(linea.precio_total)),
        Decimal.cero(),
      ),
    [lineas],
  );

  const limpiar = useCallback(() => setLineas([]), []);

  const cantidadPiezas = useMemo(
    () => lineas.reduce((acumulado, linea) => acumulado.suma(linea.cantidad), Decimal.cero()),
    [lineas],
  );

  return {
    lineas,
    agregar,
    quitar,
    cambiarCantidad,
    cambiarPrecio,
    cambiarMotivo,
    limpiar,
    total,
    cantidadPiezas,
    lineasConDescuento,
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
