import { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Field, Input, Select } from '@/design-system';
import { Decimal } from '@/shared/format/decimal';
import { parsearEntradaNumerica } from '@/shared/format/entrada';
import {
  etiquetaEstado,
  formatearCantidad,
  formatearEnUnidadLegible,
  formatearEquivalenciaSacos,
  formatearMoneda,
} from '@/shared/format/formato';
import { lotesApi } from '@/shared/api/endpoints';
import type { LoteResumen, Presentacion } from '@/shared/types/api';
import type { LineaCarrito, ResultadoBusqueda } from './tipos';
import { precioDeLote } from './SelectorLote';

export interface PeticionLote {
  producto: { id: number; nombre: string; codigo: string };
  presentacion: Presentacion;
  cantidad: string;
  lotes: LoteResumen[];
}

interface Propiedades {
  resultado: ResultadoBusqueda;
  onAgregar: (linea: Omit<LineaCarrito, 'id'>) => void;
  /** Se invoca cuando el producto tiene varios lotes: el cajero debe elegir. */
  onSeleccionarLote?: (peticion: PeticionLote) => void;
}

const TONO_ESTADO = {
  agotado: 'peligro',
  bajo_minimo: 'aviso',
  disponible: 'marca',
} as const;

/** Línea de carrito a partir de una presentación y (opcionalmente) un lote. */
function construirLinea(
  resultado: ResultadoBusqueda,
  presentacion: Presentacion,
  cantidad: Decimal,
  lote: LoteResumen | null,
): Omit<LineaCarrito, 'id'> {
  const precio = lote ? precioDeLote(lote, presentacion.id) : Decimal.desde(presentacion.precio_venta);
  const total = precio.multiplica(cantidad).redondear(2);
  return {
    producto_id: resultado.producto_id,
    presentacion_id: presentacion.id,
    producto_nombre: resultado.nombre,
    producto_codigo: resultado.codigo,
    presentacion_nombre: presentacion.nombre,
    unidad_base: resultado.unidad_base,
    factor_base: presentacion.factor_base,
    precio_original: precio.aTexto(),
    precio_total: total.aTexto(),
    precio_total_original: total.aTexto(),
    cantidad: cantidad.aTexto(),
    lote_id: lote?.id ?? null,
    lote_codigo: lote?.codigo_lote ?? null,
    lote_fecha_ingreso: lote?.fecha_ingreso ?? null,
  };
}

/** Fila de resultado de búsqueda: nombre, presentación, stock y acción de añadir. */
export function FilaResultado({ resultado, onAgregar, onSeleccionarLote }: Propiedades) {
  const presentacionesVenta = useMemo(
    () => resultado.presentaciones.filter((item) => item.activo && item.es_venta),
    [resultado.presentaciones],
  );

  const [presentacionId, setPresentacionId] = useState<number>(
    presentacionesVenta[0]?.id ?? 0,
  );
  const [cantidad, setCantidad] = useState('1');
  const [consultando, setConsultando] = useState(false);

  useEffect(() => {
    if (!presentacionesVenta.some((item) => item.id === presentacionId)) {
      setPresentacionId(presentacionesVenta[0]?.id ?? 0);
    }
  }, [presentacionesVenta, presentacionId]);

  const presentacion = presentacionesVenta.find((item) => item.id === presentacionId);
  const cantidadNumero = parsearEntradaNumerica(cantidad);
  const cantidadValida = cantidadNumero !== '' && Decimal.desde(cantidadNumero).comparar(0) > 0;

  /**
   * Al añadir se consultan los lotes del producto:
   * - sin lotes o un solo lote → se agrega directamente;
   * - varios lotes → el cajero elige (o se reparten con PEPS).
   */
  async function agregar() {
    if (!presentacion || !cantidadValida) return;
    setConsultando(true);
    try {
      const lotes = await lotesApi.listar(resultado.producto_id, { solo_con_stock: true });
      if (lotes.length > 1 && onSeleccionarLote) {
        onSeleccionarLote({
          producto: {
            id: resultado.producto_id,
            nombre: resultado.nombre,
            codigo: resultado.codigo,
          },
          presentacion,
          cantidad: cantidadNumero,
          lotes,
        });
        return;
      }
      const lote = lotes[0] ?? null;
      onAgregar(construirLinea(resultado, presentacion, Decimal.desde(cantidadNumero), lote));
    } catch {
      // Si no se pueden consultar los lotes, se cobra al precio de la presentacion.
      onAgregar(construirLinea(resultado, presentacion, Decimal.desde(cantidadNumero), null));
    } finally {
      setConsultando(false);
    }
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
            {resultado.cantidad_presentacion && resultado.presentacion_principal
              ? `${formatearEquivalenciaSacos(
                  resultado.cantidad_presentacion,
                  resultado.presentacion_principal,
                )} (${formatearEnUnidadLegible(resultado.stock_base, resultado.unidad_base)})`
              : formatearEnUnidadLegible(resultado.stock_base, resultado.unidad_base)}
          </span>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-end gap-2">
        <div className="min-w-[190px] flex-1">
          <Field
            htmlFor={`presentacion-${resultado.producto_id}`}
            etiqueta="Presentación de venta"
            ejemplo="botella"
            compacto
          >
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
          </Field>
        </div>

        <div className="w-[110px]">
          <Field
            htmlFor={`cantidad-${resultado.producto_id}`}
            etiqueta="Cantidad"
            ejemplo="1"
            compacto
            error={
              cantidad !== '' && !cantidadValida ? 'Debe ser un número mayor que cero.' : undefined
            }
          >
            <Input
              id={`cantidad-${resultado.producto_id}`}
              className="numero"
              inputMode="decimal"
              invalido={cantidad !== '' && !cantidadValida}
              value={cantidad}
              onChange={(evento) => setCantidad(evento.target.value)}
              onKeyDown={(evento) => {
                if (evento.key === 'Enter') {
                  evento.preventDefault();
                  void agregar();
                }
              }}
            />
          </Field>
        </div>

        {presentacion?.permite_fraccion ? (
          <div className="flex items-center gap-1 pb-0.5" aria-label="Atajos de fracción de saco">
            <Button
              variante={cantidadNumero === '0.5' ? 'primario' : 'secundario'}
              tamano="sm"
              onClick={() => setCantidad('0,5')}
              title="Medio saco (0,5)"
            >
              1/2
            </Button>
            <Button
              variante={cantidadNumero === '1' ? 'primario' : 'secundario'}
              tamano="sm"
              onClick={() => setCantidad('1')}
              title="Un saco entero (1)"
            >
              1
            </Button>
          </div>
        ) : null}

        <Button
          variante="secundario"
          onClick={() => void agregar()}
          disabled={!cantidadValida || consultando}
          cargando={consultando}
          textoCargando="Buscando lotes…"
        >
          Añadir
        </Button>
      </div>

      {presentacion ? (
        <p className="mt-2 text-xs text-muted">
          1 {presentacion.nombre} = {formatearCantidad(presentacion.factor_base)}{' '}
          {resultado.unidad_base ?? 'und'}
          {presentacion.permite_fraccion
            ? ` · admite medio saco (1/2 = ${formatearEnUnidadLegible(
                Decimal.desde(presentacion.factor_base).divide('2', 4),
                resultado.unidad_base,
              )})`
            : ''}
        </p>
      ) : null}
    </article>
  );
}
