/**
 * Selector de lote para la caja.
 *
 * Aparece cuando un producto tiene varios lotes con existencias. Propone el
 * lote más antiguo (PEPS) y deja que el cajero elija o reparta la cantidad
 * entre lotes, viendo el precio y el importe de cada uno antes de confirmar.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
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
import { Decimal, type EntradaDecimal } from '@/shared/format/decimal';
import { parsearEntradaNumerica } from '@/shared/format/entrada';
import {
  formatearCantidad,
  formatearEnUnidadLegible,
  formatearEquivalenciaSacos,
  formatearFecha,
  formatearMoneda,
  formatearStockEnPresentacion,
} from '@/shared/format/formato';
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
  /**
   * Cantidad ya pendiente en el carrito por lote (en unidad base).
   * Se descuenta del stock del lote para que el cajero vea la disponibilidad
   * real y no arme una venta que el servidor va a rechazar.
   */
  pendientesPorLote?: Record<number, string>;
  onConfirmar: (asignaciones: AsignacionLote[]) => void;
}

/** Precio de una presentación dentro de un lote (si el lote no lo tiene, el del lote). */
export function precioDeLote(lote: LoteResumen, presentacionId: number): Decimal {
  const precio = lote.precios.find((item) => item.presentacion_id === presentacionId);
  return Decimal.desde(precio?.precio ?? lote.precio_venta);
}
function textoDecimalLimpio(valor: Decimal): string {
  const texto = valor.aTexto();
  if (!texto.includes('.')) return texto;
  return texto.replace(/\.?0+$/, '') || '0';
}

/**
 * Cantidad disponible del lote expresada en la presentación elegida
 * (p. ej. 20 000 g / 40 000 g = 0.5 sacos = 1/2 saco).
 *
 * `pendienteBase` es lo que ya está en el carrito para ese lote: se descuenta
 * para no ofrecer más mercadería de la que queda.
 */
export function disponibleEnPresentacion(
  lote: LoteResumen,
  factorBase: EntradaDecimal = '1',
  pendienteBase: EntradaDecimal = '0',
): Decimal {
  const factor = Decimal.desde(factorBase);
  const factorSeguro = factor.comparar(Decimal.cero()) > 0 ? factor : Decimal.desde('1');
  const disponibleBase = Decimal.desde(lote.cantidad_disponible).resta(pendienteBase);
  if (disponibleBase.comparar(Decimal.cero()) < 0) return Decimal.cero();
  if (factorSeguro.comparar('1') === 0) return disponibleBase;
  return disponibleBase.divide(factorSeguro, 4);
}

/**
 * Orden en que se propone el reparto: primero los lotes cuya presentación
 * coincide con la de venta (así se termina el saco del mismo formato) y dentro
 * de cada grupo el más antiguo (PEPS).
 */
export function ordenDeLotes(
  lotes: LoteResumen[],
  presentacionId: number,
): LoteResumen[] {
  return [...lotes].sort((a, b) => {
    const coincideA = a.presentacion_id === presentacionId ? 0 : 1;
    const coincideB = b.presentacion_id === presentacionId ? 0 : 1;
    if (coincideA !== coincideB) return coincideA - coincideB;
    const fechaA = a.fecha_ingreso ?? '';
    const fechaB = b.fecha_ingreso ?? '';
    if (fechaA !== fechaB) return fechaA < fechaB ? -1 : 1;
    return a.id - b.id;
  });
}

/**
 * Reparto sugerido (PEPS): se completa la cantidad pedida con el lote más
 * antiguo disponible, pasando al siguiente si el primero no alcanza.
 * Convierte el stock base del lote (gramos/unidades) a la presentación de venta
 * (sacos/medios sacos) y descuenta lo que ya está en el carrito.
 */
export function repartoSugerido(
  lotes: LoteResumen[],
  presentacionId: number,
  cantidad: string,
  factorBase: EntradaDecimal = '1',
  pendientesPorLote: Record<number, string> = {},
) {
  let restante = Decimal.desde(cantidad);
  const suggested = new Map<number, string>();
  for (const lote of ordenDeLotes(lotes, presentacionId)) {
    if (restante.comparar(Decimal.cero()) <= 0) break;
    const disponible = disponibleEnPresentacion(
      lote,
      factorBase,
      pendientesPorLote[lote.id] ?? '0',
    );
    if (disponible.comparar(Decimal.cero()) <= 0) continue;
    const toma = restante.comparar(disponible) <= 0 ? restante : disponible;
    suggested.set(lote.id, textoDecimalLimpio(toma));
    restante = Decimal.desde(textoDecimalLimpio(restante.resta(toma)));
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
  pendientesPorLote = {},
  onConfirmar,
}: Props) {
  const [cantidades, setCantidades] = useState<Record<number, string>>({});
  const factorPresentacion = presentacion?.factor_base ?? '1';

  const suggested = useMemo(
    () =>
      repartoSugerido(
        lotes,
        presentacion?.id ?? 0,
        cantidad,
        factorPresentacion,
        pendientesPorLote,
      ),
    [lotes, presentacion?.id, cantidad, factorPresentacion, pendientesPorLote],
  );

  /** Stock real del lote: lo que queda descontando lo que ya está en el carrito. */
  const disponibleDeLote = useCallback(
    (lote: LoteResumen): Decimal =>
      disponibleEnPresentacion(lote, factorPresentacion, pendientesPorLote[lote.id] ?? '0'),
    [factorPresentacion, pendientesPorLote],
  );

  /** Lotes en el orden en que se propone el reparto (presentación que coincide y PEPS). */
  const lotesOrdenados = useMemo(
    () => ordenDeLotes(lotes, presentacion?.id ?? 0),
    [lotes, presentacion?.id],
  );

  /** Primer lote del reparto propuesto: es el que lleva la etiqueta «Sugerido». */
  const primerSugerido = useMemo(() => {
    for (const lote of lotesOrdenados) {
      if ((suggested.suggested.get(lote.id) ?? '') !== '') return lote.id;
    }
    return null;
  }, [lotesOrdenados, suggested]);

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
      const texto = parsearEntradaNumerica((cantidades[lote.id] ?? '').trim());
      if (texto === '') continue;
      const valor = Decimal.desde(texto);
      if (valor.comparar(Decimal.cero()) <= 0) continue;
      const precio = precioDeLote(lote, presentacion.id);
      resultado.push({
        lote_id: lote.id,
        lote_codigo: lote.codigo_lote,
        presentacion_id: presentacion.id,
        cantidad: textoDecimalLimpio(valor),
        precio_unitario: precio.aTexto(),
        subtotal: valor.multiplica(precio).redondear(2).aTexto(),
      });
    }
    return resultado;
  }, [lotes, cantidades, presentacion]);

  const hayExcesoEnLote = useMemo(() => {
    return lotes.some((lote) => {
      const texto = parsearEntradaNumerica((cantidades[lote.id] ?? '').trim());
      if (texto === '') return false;
      const valor = Decimal.desde(texto);
      const disp = disponibleDeLote(lote);
      return valor.comparar(disp) > 0;
    });
  }, [lotes, cantidades, disponibleDeLote]);

  const totalPedido = Decimal.desde(cantidad);
  const totalAsignado = asignaciones.reduce(
    (acumulado, item) => acumulado.suma(Decimal.desde(item.cantidad)),
    Decimal.cero(),
  );
  const completo = totalAsignado.comparar(totalPedido) === 0 && !hayExcesoEnLote;
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
            {lotesOrdenados.map((lote) => {
              const precio = precioDeLote(lote, presentacion?.id ?? 0);
              const asignado = (cantidades[lote.id] ?? '').trim();
              const valor = Decimal.desde(parsearEntradaNumerica(asignado) || '0');
              const importe = valor.multiplica(precio);
              const esSugerido = lote.id === primerSugerido;
              const pendiente = pendientesPorLote[lote.id] ?? '0';
              const disponibleBase = Decimal.desde(lote.cantidad_disponible).resta(pendiente);
              const stockLegible = formatearStockEnPresentacion(
                disponibleBase.aTexto(),
                factorPresentacion,
                presentacion?.nombre ?? lote.presentacion_nombre,
                lote.unidad_base,
              );
              return (
                <TableRow key={lote.id}>
                  <TableCell>
                    <span className="numero font-semibold text-ink">{lote.codigo_lote}</span>
                    {esSugerido ? (
                      <Badge tono="marca" className="ml-2">
                        Sugerido
                      </Badge>
                    ) : null}
                    {lote.presentacion_id === presentacion?.id && lote.presentacion_nombre ? (
                      <span className="block text-2xs text-muted">
                        {lote.presentacion_nombre}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-xs text-muted">
                    {lote.fecha_ingreso ? formatearFecha(lote.fecha_ingreso) : 'Sin fecha'}
                  </TableCell>
                  <TableCell numerica>
                    <span className="font-semibold text-ink">{stockLegible.principal}</span>
                    {stockLegible.secundario ? (
                      <span className="block text-2xs text-muted">{stockLegible.secundario}</span>
                    ) : null}
                    {Decimal.desde(pendiente).comparar(0) > 0 ? (
                      <span className="block text-2xs text-muted">
                        ya en el carrito: {formatearEnUnidadLegible(pendiente, lote.unidad_base)}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell numerica>{formatearMoneda(precio.aTexto())}</TableCell>
                  <TableCell numerica>
                    <input
                      type="text"
                      inputMode="decimal"
                      aria-label={`Cantidad del lote ${lote.codigo_lote}`}
                      placeholder="0"
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
            Asignado {formatearEquivalenciaSacos(totalAsignado.aTexto(), presentacion?.nombre)} de{' '}
            {formatearEquivalenciaSacos(totalPedido.aTexto(), presentacion?.nombre)}
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

        {hayExcesoEnLote ? (
          <Notice tono="error" titulo="Cantidad superior al stock del lote">
            Uno de los lotes seleccionados no tiene suficientes sacos disponibles.
          </Notice>
        ) : !completo ? (
          <Notice tono="aviso" titulo="Falta completar la cantidad">
            Reparta {formatearEquivalenciaSacos(totalPedido.aTexto(), presentacion?.nombre)} entre
            los lotes antes de confirmar.
          </Notice>
        ) : null}
      </div>
    </Modal>
  );
}
