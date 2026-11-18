/**
 * Selector de lote para la caja.
 *
 * Aparece cuando un producto tiene varios lotes con existencias. Propone el
 * lote más antiguo (PEPS) y deja que el cajero elija o reparta la cantidad
 * entre lotes, viendo el precio y el importe de cada uno antes de confirmar.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Modal,
  Notice,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/design-system';
import { Decimal } from '@/shared/format/decimal';
import { formatearCantidad, formatearFecha, formatearMoneda } from '@/shared/format/formato';
import type { LoteResumen, Presentacion } from '@/shared/types/api';

export interface AsignacionLote {
  lote_id: number;
  lote_codigo: string;
  presentacion_id: number;
  cantidad: string;
  precio_unitario: string;
  subtotal: string;
}

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  producto: { id: number; nombre: string; codigo: string } | null;
  presentacion: Presentacion | null;
  cantidad: string;
  lotes: LoteResumen[];
  onConfirmar: (asignaciones: AsignacionLote[]) => void;
}

/** Precio de una presentación dentro de un lote (si el lote no lo tiene, el del lote). */
export function precioDeLote(lote: LoteResumen, presentacionId: number): Decimal {
  const precio = lote.precios.find((item) => item.presentacion_id === presentacionId);
  return Decimal.desde(precio?.precio ?? lote.precio_venta);
}
/**
 * Reparto sugerido (PEPS): se completa la cantidad pedida con el lote más
 * antiguo disponible, pasando al siguiente si el primero no alcanza.
 */
export function repartoSugerido(lotes: LoteResumen[], _presentacionId: number, cantidad: string) {
  let restante = Decimal.desde(cantidad);
  const suggested = new Map<number, string>();
  for (const lote of lotes) {
    if (restante.comparar(Decimal.cero()) <= 0) break;
    const disponible = Decimal.desde(lote.cantidad_disponible);
    if (disponible.comparar(Decimal.cero()) <= 0) continue;
    const toma = restante.comparar(disponible) <= 0 ? restante : disponible;
    suggested.set(lote.id, toma.aTexto());
    restante = restante.resta(toma);
  }
  return { suggested, restante };
}

export function SelectorLote({
  abierto,
  onCerrar,
  producto,
  presentacion,
  cantidad,
  lotes,
  onConfirmar,
}: Props) {
  const [cantidades, setCantidades] = useState<Record<number, string>>({});

  const suggested = useMemo(
    () => repartoSugerido(lotes, presentacion?.id ?? 0, cantidad),
    [lotes, presentacion?.id, cantidad],
  );

  useEffect(() => {
    if (!abierto) return;
    const inicial: Record<number, string> = {};
    suggested.suggested.forEach((valor, loteId) => {
      inicial[loteId] = valor;
    });
    setCantidades(inicial);
  }, [abierto, suggested]);

  const asignaciones = useMemo(() => {
    if (!presentacion) return [];
    const resultado: AsignacionLote[] = [];
    for (const lote of lotes) {
      const texto = (cantidades[lote.id] ?? '').trim();
      if (texto === '') continue;
      const valor = Decimal.desde(texto);
      if (valor.comparar(Decimal.cero()) <= 0) continue;
      const precio = precioDeLote(lote, presentacion.id);
      resultado.push({
        lote_id: lote.id,
        lote_codigo: lote.codigo_lote,
        presentacion_id: presentacion.id,
        cantidad: valor.aTexto(),
        precio_unitario: precio.aTexto(),
        subtotal: valor.multiplica(precio).redondear(2).aTexto(),
      });
    }
    return resultado;
  }, [lotes, cantidades, presentacion]);

  const totalPedido = Decimal.desde(cantidad);
  const totalAsignado = asignaciones.reduce(
    (acumulado, item) => acumulado.suma(Decimal.desde(item.cantidad)),
    Decimal.cero(),
  );
  const completo = totalAsignado.comparar(totalPedido) === 0;
  const hayPreciosDistintos = lotes.some(
    (lote) => precioDeLote(lote, presentacion?.id ?? 0).aTexto() !== precioDeLote(lotes[0], presentacion?.id ?? 0).aTexto(),
  );

  function confirmar() {
    if (asignaciones.length === 0) return;
    onConfirmar(asignaciones);
  }

  return (
    <Modal
      abierto={abierto}
      titulo="Elegir el lote de venta"
      descripcion={
        producto
          ? `${producto.nombre} · ${presentacion?.nombre ?? ''} · pide ${formatearCantidad(cantidad)}`
          : undefined
      }
      ancho="lg"
      onCerrar={onCerrar}
      pie={
        <>
          <Button variante="secundario" onClick={onCerrar}>
            Cancelar
          </Button>
          <Button variante="primario" disabled={!completo} onClick={confirmar}>
            Agregar al carrito
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {hayPreciosDistintos ? (
          <Notice tono="aviso" titulo="Este producto tiene varios precios">
            Cada lote tiene su propio precio de venta. Se propone el lote más antiguo para
            terminar el stock viejo, pero puede vender el que prefiera: ajuste las cantidades y
            revise los importes antes de confirmar.
          </Notice>
        ) : (
          <Notice tono="info" titulo="Varios lotes al mismo precio">
            Los lotes tienen el mismo precio de venta, así que se reparten del más antiguo al más
            reciente (PEPS). Puede cambiar el reparto si lo necesita.
          </Notice>
        )}

        <Table descripcion="Lotes disponibles del producto">
          <TableHead>
            <TableHeader>Lote</TableHeader>
            <TableHeader>Ingreso</TableHeader>
            <TableHeader className="text-right">Stock</TableHeader>
            <TableHeader className="text-right">Precio</TableHeader>
            <TableHeader className="text-right">Cantidad</TableHeader>
            <TableHeader className="text-right">Importe</TableHeader>
          </TableHead>
          <TableBody>
            {lotes.map((lote, indice) => {
              const precio = precioDeLote(lote, presentacion?.id ?? 0);
              const asignado = (cantidades[lote.id] ?? '').trim();
              const valor = Decimal.desde(asignado || '0');
              const importe = valor.multiplica(precio);
              const esSugerido = (suggested.suggested.get(lote.id) ?? '') !== '' && indice === 0;
              return (
                <TableRow key={lote.id}>
                  <TableCell>
                    <span className="numero font-semibold text-ink">{lote.codigo_lote}</span>
                    {esSugerido ? (
                      <Badge tono="marca" className="ml-2">
                        Sugerido
                      </Badge>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-xs text-muted">
                    {lote.fecha_ingreso ? formatearFecha(lote.fecha_ingreso) : 'Sin fecha'}
                  </TableCell>
                  <TableCell numerica>
                    {formatearCantidad(lote.cantidad_disponible)}
                  </TableCell>
                  <TableCell numerica>{formatearMoneda(precio.aTexto())}</TableCell>
                  <TableCell numerica>
                    <input
                      type="text"
                      inputMode="decimal"
                      aria-label={`Cantidad del lote ${lote.codigo_lote}`}
                      className="numero w-[88px] rounded-[6px] border border-linea bg-surface px-2 py-1 text-right text-sm text-ink"
                      value={asignado}
                      onChange={(evento) =>
                        setCantidades((actuales) => ({
                          ...actuales,
                          [lote.id]: evento.target.value,
                        }))
                      }
                    />
                  </TableCell>
                  <TableCell numerica className="font-semibold">
                    {formatearMoneda(importe.redondear(2).aTexto())}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-muted">
            Asignado {formatearCantidad(totalAsignado.aTexto())} de{' '}
            {formatearCantidad(totalPedido.aTexto())}
          </span>
          <span className="font-semibold numero text-ink">
            Total {formatearMoneda(
              asignaciones
                .reduce(
                  (acumulado, item) => acumulado.suma(Decimal.desde(item.subtotal)),
                  Decimal.cero(),
                )
                .aTexto(),
            )}
          </span>
        </div>

        {!completo ? (
          <Notice tono="aviso" titulo="Falta completar la cantidad">
            Reparta las {formatearCantidad(totalPedido.aTexto())} entre los lotes antes de
            confirmar.
          </Notice>
        ) : null}
      </div>
    </Modal>
  );
}
