import { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Input, Select } from '@/design-system';
import { Decimal } from '@/shared/format/decimal';
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

  const cantidadValida = Decimal.desde(cantidad).comparar(0) > 0;
  const costoValido = Decimal.desde(costo).comparar(0) >= 0;

  function agregar() {
    if (!presentacion || !cantidadValida || !costoValido) return;
    onAgregar({
      producto_id: productoId,
      presentacion_id: presentacion.id,
      presentacion_nombre: presentacion.nombre,
      factor_base: presentacion.factor_base,
      producto_nombre: nombre,
      producto_codigo: codigo,
      unidad_base: unidadBase ?? null,
      cantidad: Decimal.desde(cantidad).aTexto(),
      costo_unitario: Decimal.desde(costo).aTexto(),
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
            <label htmlFor={`presentacion-ingreso-${productoId}`} className="sr-only">
              Presentación de compra de {nombre}
            </label>
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
          </div>

          <div className="w-[92px]">
            <label htmlFor={`cantidad-ingreso-${productoId}`} className="sr-only">
              Cantidad de {nombre}
            </label>
            <Input
              id={`cantidad-ingreso-${productoId}`}
              className="numero"
              inputMode="decimal"
              value={cantidad}
              onChange={(evento) => setCantidad(evento.target.value)}
            />
          </div>

          <div className="w-[120px]">
            <label htmlFor={`costo-ingreso-${productoId}`} className="sr-only">
              Costo unitario de {nombre}
            </label>
            <Input
              id={`costo-ingreso-${productoId}`}
              className="numero"
              inputMode="decimal"
              prefijo="S/"
              value={costo}
              onChange={(evento) => setCosto(evento.target.value)}
            />
          </div>

          <Button variante="secundario" onClick={agregar} disabled={!cantidadValida || !costoValido}>
            Añadir
          </Button>
        </div>
      )}

      {presentacion ? (
        <p className="mt-2 text-xs text-muted">
          1 {presentacion.nombre} = {formatearCantidad(presentacion.factor_base)}{' '}
          {unidadBase?.toLowerCase() ?? 'und'}
        </p>
      ) : null}
    </article>
  );
}
