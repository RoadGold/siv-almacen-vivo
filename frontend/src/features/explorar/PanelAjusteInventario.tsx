/**
 * Ajuste administrativo de inventario y carga de saldo inicial.
 *
 * No existe un botón de «editar stock»: toda corrección se registra como una
 * operación administrativa con motivo, y queda en el Kardex y en la auditoría.
 *
 * Cuando el producto tiene varios lotes con existencias, el ajuste debe
 * indicar a qué lote se aplica: nunca se reparte solo entre lotes.
 */

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Field, Input, Modal, Notice, Select, useToast } from '@/design-system';
import { ErrorApi } from '@/shared/api/client';
import { inventarioApi } from '@/shared/api/endpoints';
import { abreviarUnidad, formatearCantidad, formatearFecha } from '@/shared/format/formato';
import { mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { Decimal } from '@/shared/format/decimal';
import type { LoteResumen } from '@/shared/types/api';

export type ModoAjuste = 'ajuste' | 'saldo-inicial';

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  modo: ModoAjuste;
  producto: { id: number; nombre: string; codigo: string; unidad_base?: string | null } | null;
  almacenId: number | null;
  existenciaBase: string;
  /** Lotes del producto: se usa para exigir el lote afectado. */
  lotes: LoteResumen[];
}

/** Cuerpo del ajuste. `lote_id` forma parte del contrato del API. */
interface CuerpoAjuste {
  almacen_id: number;
  producto_id: number;
  cantidad_base: string;
  motivo: string;
  lote_id?: number;
}

function decimal(texto: string): Decimal {
  return Decimal.desde((texto || '0').trim() || '0');
}

/** Lotes con existencias: solo ellos pueden recibir un ajuste. */
export function lotesConExistencias(lotes: LoteResumen[]): LoteResumen[] {
  return lotes.filter((lote) => decimal(lote.cantidad_disponible).comparar(0) > 0);
}

/**
 * Lote afectado por el ajuste.
 * Con un único lote con existencias se elige automáticamente (y se muestra su
 * código); con varios hay que elegirlo y, si no, no se puede registrar.
 */
export function loteAfectado(
  lotesConStock: LoteResumen[],
  loteId: number | '',
): LoteResumen | null {
  if (lotesConStock.length === 1) return lotesConStock[0];
  if (loteId === '') return null;
  return lotesConStock.find((lote) => lote.id === loteId) ?? null;
}

export function PanelAjusteInventario({
  abierto,
  onCerrar,
  modo,
  producto,
  almacenId,
  existenciaBase,
  lotes,
}: Props) {
  const [cantidad, setCantidad] = useState('');
  const [costo, setCosto] = useState('0');
  const [motivo, setMotivo] = useState('');
  const [loteId, setLoteId] = useState<number | ''>('');
  const [error, setError] = useState<string | null>(null);
  const [lotesDelError, setLotesDelError] = useState<{ id: number; codigo_lote: string }[]>([]);
  const cliente = useQueryClient();
  const { notificar } = useToast();

  /** Lotes con existencias: solo ellos pueden recibir un ajuste. */
  const lotesConStock = useMemo(() => lotesConExistencias(lotes), [lotes]);

  /** Con más de un lote con stock hay que elegir el afectado. */
  const requiereLote = lotesConStock.length > 1;
  /** Con un único lote con stock se elige automáticamente. */
  const loteElegido = loteAfectado(lotesConStock, loteId);

  useEffect(() => {
    if (abierto) {
      setCantidad('');
      setCosto('0');
      setMotivo('');
      setError(null);
      setLotesDelError([]);
      setLoteId('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, producto?.id, modo]);

  const esSaldoInicial = modo === 'saldo-inicial';

  const registrar = useMutation({
    mutationFn: async () => {
      if (!producto) throw new Error('Producto no seleccionado.');
      const valor = decimal(cantidad);
      if (esSaldoInicial) {
        if (valor.comparar(Decimal.cero()) <= 0) {
          throw new Error('La cantidad del saldo inicial debe ser mayor que cero.');
        }
        return inventarioApi.inventarioInicial({
          almacen_id: almacenId,
          referencia: motivo.trim() || 'Inventario inicial',
          lineas: [
            {
              producto_id: producto.id,
              cantidad_base: valor.aTexto(),
              costo_unitario_base: decimal(costo).aTexto(),
            },
          ],
        });
      }
      if (valor.esCero()) {
        throw new Error('El ajuste debe ser distinto de cero.');
      }
      if (motivo.trim().length < 5) {
        throw new Error('Escriba el motivo del ajuste (mínimo 5 caracteres).');
      }
      if (!almacenId) throw new Error('No se pudo determinar el almacén.');
      if (requiereLote && !loteElegido) {
        throw new Error('Seleccione el lote al que se aplica el ajuste.');
      }
      // `lote_id` es parte del contrato del API (el backend lo exige cuando el
      // producto tiene varios lotes con existencias). El cliente compartido
      // todavía no lo declara en su tipo, así que el cuerpo se arma aquí con
      // ese campo incluido.
      const cuerpo: CuerpoAjuste = {
        almacen_id: almacenId,
        producto_id: producto.id,
        cantidad_base: valor.aTexto(),
        motivo: motivo.trim(),
      };
      if (loteElegido) cuerpo.lote_id = loteElegido.id;
      return inventarioApi.ajustar(cuerpo);
    },
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ['inventario'] });
      cliente.invalidateQueries({ queryKey: ['lotes'] });
      cliente.invalidateQueries({ queryKey: ['dashboard'] });
      registrarOperacion(
        esSaldoInicial ? 'Carga de inventario inicial' : 'Ajuste de inventario',
      );
      notificar(
        esSaldoInicial
          ? 'Saldo inicial registrado.'
          : 'Ajuste registrado y anotado en el Kardex.',
        'exito',
      );
      onCerrar();
    },
    onError: (fallo) => {
      setError(mensajeDeError(fallo));
      // El servidor responde 400 con el detalle de los lotes cuando falta elegirlos.
      if (fallo instanceof ErrorApi) {
        const detalle = fallo.detalle?.lotes;
        if (Array.isArray(detalle)) {
          setLotesDelError(
            detalle as { id: number; codigo_lote: string }[],
          );
        }
      }
    },
  });

  const cantidadActual = decimal(existenciaBase);
  const cantidadIngresada = decimal(cantidad);
  const resultado = esSaldoInicial ? cantidadIngresada : cantidadActual.suma(cantidadIngresada);
  const unidad = producto?.unidad_base ?? null;

  // Impacto sobre el lote elegido.
  const stockLoteAntes = loteElegido ? decimal(loteElegido.cantidad_disponible) : null;
  const stockLoteDespues = stockLoteAntes
    ? stockLoteAntes.suma(cantidadIngresada)
    : null;

  const faltaElegirLote = !esSaldoInicial && requiereLote && !loteElegido;

  return (
    <Modal
      abierto={abierto}
      onCerrar={onCerrar}
      titulo={esSaldoInicial ? 'Cargar saldo inicial' : 'Registrar ajuste de inventario'}
      descripcion={
        producto ? `${producto.nombre} · ${producto.codigo}` : 'Seleccione un producto del catálogo.'
      }
      pie={
        <>
          <Button variante="secundario" onClick={onCerrar}>
            Cancelar
          </Button>
          <Button
            onClick={() => {
              setError(null);
              registrar.mutate();
            }}
            disabled={registrar.isPending || !producto || faltaElegirLote}
          >
            {registrar.isPending
              ? 'Registrando…'
              : esSaldoInicial
                ? 'Registrar saldo inicial'
                : 'Registrar ajuste'}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error ? (
          <Notice tono="error" titulo="No se pudo registrar">
            {error}
          </Notice>
        ) : null}

        {lotesDelError.length > 0 ? (
          <Notice tono="aviso" titulo="Elige el lote afectado">
            <ul className="mt-1 flex flex-wrap gap-2">
              {lotesDelError.map((lote) => (
                <li key={lote.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setLoteId(lote.id);
                      setLotesDelError([]);
                      setError(null);
                    }}
                    className="rounded-[6px] border border-linea-fuerte px-2 py-1 text-xs font-semibold text-ink hover:border-brand hover:text-brand"
                  >
                    {lote.codigo_lote}
                  </button>
                </li>
              ))}
            </ul>
          </Notice>
        ) : null}

        <Notice tono="info" titulo={esSaldoInicial ? 'Carga inicial' : 'Operación administrativa'}>
          {esSaldoInicial
            ? 'El saldo inicial NO es una compra: se registra como SALDO_INICIAL y queda diferenciado de los ingresos de proveedor en el Kardex y en la auditoría.'
            : 'El ajuste suma (cantidad positiva) o resta (cantidad negativa) existencias y queda registrado con su motivo, su usuario y la fecha.'}
        </Notice>

        {!esSaldoInicial ? (
          <div className="rounded-[6px] border border-linea bg-surface-tenue px-4 py-3 text-sm">
            <p className="etiqueta">Existencia actual</p>
            <p className="numero mt-1 text-lg font-bold text-ink">
              {formatearCantidad(existenciaBase || '0')} {abreviarUnidad(unidad)}
            </p>
          </div>
        ) : null}

        {/* --- Selección del lote afectado --- */}
        {!esSaldoInicial && lotesConStock.length > 0 ? (
          <Field
            htmlFor="ajuste-lote"
            etiqueta="Lote afectado"
            obligatorio={requiereLote}
            ayuda={
              requiereLote
                ? 'Este producto tiene varios lotes con existencias: el ajuste se aplica solo al lote que elijas. Los códigos lucen así: F001-00123.'
                : `El producto tiene un único lote con existencias: el ajuste se aplicará al lote ${lotesConStock[0].codigo_lote}.`
            }
            error={faltaElegirLote ? 'Seleccione el lote para poder registrar el ajuste.' : undefined}
          >
            <Select
              id="ajuste-lote"
              value={loteElegido?.id ?? ''}
              invalido={faltaElegirLote}
              onChange={(evento) => setLoteId(Number(evento.target.value))}
            >
              <option value="">Selecciona un lote…</option>
              {lotesConStock.map((lote) => (
                <option key={lote.id} value={lote.id}>
                  {lote.codigo_lote} ·{' '}
                  {lote.fecha_ingreso ? formatearFecha(lote.fecha_ingreso) : 'sin fecha'} ·{' '}
                  {formatearCantidad(lote.cantidad_disponible)} {abreviarUnidad(unidad)}
                </option>
              ))}
            </Select>
          </Field>
        ) : null}

        <Field
          htmlFor="ajuste-cantidad"
          etiqueta="Cantidad"
          ejemplo={esSaldoInicial ? '120' : '-2'}
          ayuda={
            esSaldoInicial
              ? 'Unidades, gramos o mililitros según la unidad base del producto.'
              : 'Positivo suma existencias y negativo las resta. Ejemplo: -2 para una rotura de dos unidades.'
          }
        >
          <Input
            id="ajuste-cantidad"
            type="text"
            inputMode="decimal"
            className="numero"
            value={cantidad}
            onChange={(evento) => setCantidad(evento.target.value)}
          />
        </Field>

        {esSaldoInicial ? (
          <Field
            htmlFor="ajuste-costo"
            etiqueta="Costo unitario"
            ejemplo="12,50"
            ayuda="Costo por unidad base. Si no lo conoce, deje 0 y se corregirá con el primer ingreso."
          >
            <Input
              id="ajuste-costo"
              type="text"
              inputMode="decimal"
              className="numero"
              value={costo}
              onChange={(evento) => setCosto(evento.target.value)}
            />
          </Field>
        ) : null}

        <Field
          htmlFor="ajuste-motivo"
          etiqueta={esSaldoInicial ? 'Referencia del conteo' : 'Motivo del ajuste'}
          ejemplo={esSaldoInicial ? 'Conteo de apertura' : 'Rotura durante el manipuleo'}
          ayuda={
            esSaldoInicial
              ? 'Por ejemplo: «Conteo de apertura» o «Diferencia de inventario inicial».'
              : 'Obligatorio (mínimo 5 caracteres). Ejemplo: «Rotura durante el manipuleo».'
          }
        >
          <Input
            id="ajuste-motivo"
            type="text"
            value={motivo}
            onChange={(evento) => setMotivo(evento.target.value)}
          />
        </Field>

        {!esSaldoInicial ? (
          <div className="rounded-[6px] border border-linea px-4 py-3 text-sm">
            <p className="etiqueta">Impacto</p>
            <p className="numero mt-1 font-bold text-ink">
              {formatearCantidad(cantidadActual.aTexto())} → {formatearCantidad(resultado.aTexto())}{' '}
              {abreviarUnidad(unidad)}
            </p>
            {loteElegido && stockLoteAntes && stockLoteDespues ? (
              <p className="numero mt-1 text-sm text-ink">
                Lote {loteElegido.codigo_lote}: {formatearCantidad(stockLoteAntes.aTexto())} →{' '}
                {formatearCantidad(stockLoteDespues.aTexto())} {abreviarUnidad(unidad)}
              </p>
            ) : null}
            {resultado.comparar(Decimal.cero()) < 0 ? (
              <p className="mt-1 text-xs font-semibold text-danger">
                El resultado sería negativo: el sistema lo rechazará.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
