import { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Input, Select } from '@/design-system';
import { Decimal } from '@/shared/format/decimal';
import { etiquetaEstado, formatearCantidad, formatearMoneda } from '@/shared/format/formato';
import type { LineaCarrito, ResultadoBusqueda } from './tipos';

interface Propiedades {
  resultado: ResultadoBusqueda;
  onAgregar: (linea: Omit<LineaCarrito, 'id'>) => void;
}

const TONO_ESTADO = {
  agotado: 'peligro',
  bajo_minimo: 'aviso',
  disponible: 'marca',
} as const;

/** Fila de resultado de búsqueda: nombre, presentación, stock y acción de añadir. */
export function FilaResultado({ resultado, onAgregar }: Propiedades) {
  const presentacionesVenta = useMemo(
    () => resultado.presentaciones.filter((item) => item.activo && item.es_venta),
    [resultado.presentaciones],
  );

  const [presentacionId, setPresentacionId] = useState<number>(
    presentacionesVenta[0]?.id ?? 0,
  );
  const [cantidad, setCantidad] = useState('1');

  useEffect(() => {
    if (!presentacionesVenta.some((item) => item.id === presentacionId)) {
      setPresentacionId(presentacionesVenta[0]?.id ?? 0);
    }
  }, [presentacionesVenta, presentacionId]);

  const presentacion = presentacionesVenta.find((item) => item.id === presentacionId);
  const cantidadDecimal = Decimal.desde(cantidad);
  const valida = Boolean(presentacion) && cantidadDecimal.comparar(0) > 0;

  function agregar() {
    if (!presentacion || !valida) return;
    onAgregar({
      producto_id: resultado.producto_id,
      presentacion_id: presentacion.id,
      producto_nombre: resultado.nombre,
      producto_codigo: resultado.codigo,
      presentacion_nombre: presentacion.nombre,
      unidad_base: resultado.unidad_base,
      factor_base: presentacion.factor_base,
      precio_unitario: presentacion.precio_venta,
      precio_original: presentacion.precio_venta,
      cantidad: cantidadDecimal.aTexto(),
    });
  }

  return (
    <article className="border-b border-linea px-4 py-3 last:border-b-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-ink">{resultado.nombre}</h3>
          <p className="text-xs text-muted">
            Código {resultado.codigo}
            {resultado.presentacion_principal
              ? ` · presentación habitual: ${resultado.presentacion_principal}`
              : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tono={TONO_ESTADO[resultado.estado as keyof typeof TONO_ESTADO] ?? 'neutro'}>
            {etiquetaEstado(resultado.estado)}
          </Badge>
          <span className="text-xs numero text-ink-suave">
            {formatearCantidad(resultado.cantidad_presentacion ?? resultado.stock_base)} ·{' '}
            {resultado.unidad_base ?? 'und'}
          </span>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-end gap-2">
        <div className="min-w-[190px] flex-1">
          <label htmlFor={`presentacion-${resultado.producto_id}`} className="sr-only">
            Presentación de venta para {resultado.nombre}
          </label>
          <Select
            id={`presentacion-${resultado.producto_id}`}
            value={presentacionId || ''}
            onChange={(evento) => setPresentacionId(Number(evento.target.value))}
            disabled={presentacionesVenta.length === 0}
          >
            {presentacionesVenta.length === 0 ? (
              <option value="">Sin presentaciones de venta</option>
            ) : null}
            {presentacionesVenta.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nombre} · {formatearMoneda(item.precio_venta)}
              </option>
            ))}
          </Select>
        </div>

        <div className="w-[110px]">
          <label htmlFor={`cantidad-${resultado.producto_id}`} className="sr-only">
            Cantidad para {resultado.nombre}
          </label>
          <Input
            id={`cantidad-${resultado.producto_id}`}
            className="numero"
            inputMode="decimal"
            value={cantidad}
            onChange={(evento) => setCantidad(evento.target.value)}
            onKeyDown={(evento) => {
              if (evento.key === 'Enter') {
                evento.preventDefault();
                agregar();
              }
            }}
          />
        </div>

        <Button variante="secundario" onClick={agregar} disabled={!valida}>
          Añadir
        </Button>
      </div>

      {presentacion ? (
        <p className="mt-2 text-xs text-muted">
          1 {presentacion.nombre} = {formatearCantidad(presentacion.factor_base)}{' '}
          {resultado.unidad_base ?? 'und'}
          {presentacion.permite_fraccion ? ' · admite fracciones' : ''}
        </p>
      ) : null}
    </article>
  );
}
