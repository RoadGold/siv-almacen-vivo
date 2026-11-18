import { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Field, Input, Select } from '@/design-system';
import { Decimal } from '@/shared/format/decimal';
import { parsearEntradaNumerica } from '@/shared/format/entrada';
import { formatearCantidad, formatearMoneda } from '@/shared/format/formato';
import type { Presentacion } from '@/shared/types/api';

export interface DatosLineaIngreso {
  producto_id: number;
  presentacion_id: number;
  presentacion_nombre: string;
  factor_base: string;
  producto_nombre: string;
  producto_codigo: string;
  unidad_base: string | null;
  cantidad: string;
  costo_unitario: string;
  /** Precio de venta del lote que se crea con esta línea. */
  precio_venta: string;
}

interface Propiedades {
  productoId: number;
  codigo: string;
  nombre: string;
  unidadBase?: string | null;
  presentaciones: Presentacion[];
  presentacionHabitualId?: number | null;
  ultimoCosto?: string | null;
  onAgregar: (datos: DatosLineaIngreso) => void;
  /** Indica si el producto ya está en el ingreso en curso. */
  yaAgregado?: boolean;
}

/** Fila editable de producto para el paso 2 del ingreso. */
export function FilaIngreso({
  productoId,
  codigo,
  nombre,
  unidadBase,
  presentaciones,
  presentacionHabitualId,
  ultimoCosto,
  onAgregar,
  yaAgregado = false,
}: Propiedades) {
  const presentacionesCompra = useMemo(
    () => presentaciones.filter((item) => item.activo && item.es_compra),
    [presentaciones],
  );

  const [presentacionId, setPresentacionId] = useState<number>(
    presentacionHabitualId ?? presentacionesCompra[0]?.id ?? 0,
  );
  const [cantidad, setCantidad] = useState('1');
  const [costo, setCosto] = useState(() => ultimoCosto ?? '0');
  const [precioVenta, setPrecioVenta] = useState('0');

  useEffect(() => {
    if (!presentacionesCompra.some((item) => item.id === presentacionId)) {
      setPresentacionId(presentacionHabitualId ?? presentacionesCompra[0]?.id ?? 0);
    }
  }, [presentacionesCompra, presentacionId, presentacionHabitualId]);

  const presentacion = presentacionesCompra.find((item) => item.id === presentacionId);

  useEffect(() => {
    if (!presentacion) return;
    if (!ultimoCosto || Decimal.desde(costo).esCero()) {
      setCosto(presentacion.costo_referencia ?? '0');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presentacion?.id]);

  // El precio de venta del lote se precarga con el precio vigente de la
  // presentación; el vendedor puede ajustarlo antes de confirmar la línea.
  useEffect(() => {
    if (!presentacion) return;
    setPrecioVenta(presentacion.precio_venta ?? '0');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presentacion?.id]);

  /** Valores escritos, ya normalizados (1.000 = mil, 12,50 = decimal). */
  const cantidadNumero = parsearEntradaNumerica(cantidad);
  const costoNumero = parsearEntradaNumerica(costo);
  const precioNumero = parsearEntradaNumerica(precioVenta);
  const cantidadValida = cantidadNumero !== '' && Decimal.desde(cantidadNumero).comparar(0) > 0;
  const costoValido = costoNumero !== '' && Decimal.desde(costoNumero).comparar(0) >= 0;
  const precioValido = precioNumero !== '' && Decimal.desde(precioNumero).comparar(0) >= 0;

  function agregar() {
    if (!presentacion || !cantidadValida || !costoValido || !precioValido) return;
    onAgregar({
      producto_id: productoId,
      presentacion_id: presentacion.id,
      presentacion_nombre: presentacion.nombre,
      factor_base: presentacion.factor_base,
      producto_nombre: nombre,
      producto_codigo: codigo,
      unidad_base: unidadBase ?? null,
      cantidad: cantidadNumero,
      costo_unitario: costoNumero,
      precio_venta: precioNumero,
    });
  }

  return (
    <article className="border-b border-linea px-4 py-3 last:border-b-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-ink">{nombre}</h3>
          <p className="text-xs text-muted">
            Código {codigo}
            {unidadBase ? ` · unidad base ${unidadBase.toLowerCase()}` : ''}
            {ultimoCosto ? ` · último costo ${formatearMoneda(ultimoCosto)}` : ''}
          </p>
        </div>
        {yaAgregado ? <Badge tono="marca">En el ingreso</Badge> : null}
      </div>

      {presentacionesCompra.length === 0 ? (
        <p className="mt-2 text-xs text-danger">
          Este producto no tiene presentaciones de compra. Créalas en Gestionar → Productos.
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <div className="min-w-[180px] flex-1">
            <Field
              htmlFor={`presentacion-ingreso-${productoId}`}
              etiqueta="Presentación de compra"
              ejemplo="saco 50 kg"
              compacto
            >
              <Select
                id={`presentacion-ingreso-${productoId}`}
                value={presentacionId || ''}
                onChange={(evento) => setPresentacionId(Number(evento.target.value))}
              >
                {presentacionesCompra.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre} · {formatearCantidad(item.factor_base)}{' '}
                    {unidadBase?.toLowerCase() ?? 'und'}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="w-[100px]">
            <Field
              htmlFor={`cantidad-ingreso-${productoId}`}
              etiqueta="Cantidad"
              ejemplo="10"
              compacto
              error={
                cantidad !== '' && !cantidadValida
                  ? 'Debe ser un número mayor que cero.'
                  : undefined
              }
            >
              <Input
                id={`cantidad-ingreso-${productoId}`}
                className="numero"
                inputMode="decimal"
                invalido={cantidad !== '' && !cantidadValida}
                value={cantidad}
                onChange={(evento) => setCantidad(evento.target.value)}
              />
            </Field>
          </div>

          <div className="w-[128px]">
            <Field
              htmlFor={`costo-ingreso-${productoId}`}
              etiqueta="Costo unitario"
              ejemplo="150.00"
              compacto
              error={
                costo !== '' && !costoValido ? 'No es un número válido.' : undefined
              }
            >
              <Input
                id={`costo-ingreso-${productoId}`}
                className="numero"
                inputMode="decimal"
                prefijo="S/"
                invalido={costo !== '' && !costoValido}
                value={costo}
                onChange={(evento) => setCosto(evento.target.value)}
              />
            </Field>
          </div>

          <div className="w-[128px]">
            <Field
              htmlFor={`precio-venta-ingreso-${productoId}`}
              etiqueta="Precio de venta del lote"
              ejemplo="170.00"
              compacto
              error={
                precioVenta !== '' && !precioValido ? 'No es un número válido.' : undefined
              }
            >
              <Input
                id={`precio-venta-ingreso-${productoId}`}
                className="numero"
                inputMode="decimal"
                prefijo="S/"
                invalido={precioVenta !== '' && !precioValido}
                value={precioVenta}
                onChange={(evento) => setPrecioVenta(evento.target.value)}
              />
            </Field>
          </div>

          <Button
            variante="secundario"
            onClick={agregar}
            disabled={!cantidadValida || !costoValido || !precioValido}
          >
            Añadir
          </Button>
        </div>
      )}

      {presentacion ? (
        <p className="mt-2 text-xs text-muted">
          1 {presentacion.nombre} = {formatearCantidad(presentacion.factor_base)}{' '}
          {unidadBase?.toLowerCase() ?? 'und'} · precio de venta del lote{' '}
          {formatearMoneda(precioVenta)}
        </p>
      ) : null}
    </article>
  );
}
