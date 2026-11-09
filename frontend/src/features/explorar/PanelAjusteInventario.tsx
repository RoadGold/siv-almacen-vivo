/**
 * Ajuste administrativo de inventario y carga de saldo inicial.
 *
 * No existe un botón de «editar stock»: toda corrección se registra como una
 * operación administrativa con motivo, y queda en el Kardex y en la auditoría.
 */

import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Field, Input, Modal, Notice, useToast } from '@/design-system';
import { inventarioApi } from '@/shared/api/endpoints';
import { abreviarUnidad, formatearCantidad } from '@/shared/format/formato';
import { mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { Decimal } from '@/shared/format/decimal';

export type ModoAjuste = 'ajuste' | 'saldo-inicial';

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  modo: ModoAjuste;
  producto: { id: number; nombre: string; codigo: string; unidad_base?: string | null } | null;
  almacenId: number | null;
  existenciaBase: string;
}

function decimal(texto: string): Decimal {
  return Decimal.desde((texto || '0').trim() || '0');
}

export function PanelAjusteInventario({
  abierto,
  onCerrar,
  modo,
  producto,
  almacenId,
  existenciaBase,
}: Props) {
  const [cantidad, setCantidad] = useState('');
  const [costo, setCosto] = useState('0');
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState<string | null>(null);
  const cliente = useQueryClient();
  const { notificar } = useToast();

  useEffect(() => {
    if (abierto) {
      setCantidad('');
      setCosto('0');
      setMotivo('');
      setError(null);
    }
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
      return inventarioApi.ajustar({
        almacen_id: almacenId,
        producto_id: producto.id,
        cantidad_base: valor.aTexto(),
        motivo: motivo.trim(),
      });
    },
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ['inventario'] });
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
    onError: (fallo) => setError(mensajeDeError(fallo)),
  });

  const cantidadActual = decimal(existenciaBase);
  const cantidadIngresada = decimal(cantidad);
  const resultado = esSaldoInicial ? cantidadIngresada : cantidadActual.suma(cantidadIngresada);
  const unidad = producto?.unidad_base ?? null;

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
            disabled={registrar.isPending || !producto}
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

        <Field
          htmlFor="ajuste-cantidad"
          etiqueta={
            esSaldoInicial ? 'Cantidad en unidad base' : 'Cantidad (positivo suma, negativo resta)'
          }
          ayuda={
            esSaldoInicial
              ? 'Unidades, gramos o mililitros según la unidad base del producto.'
              : 'Ejemplo: -2 para registrar una rotura de dos unidades.'
          }
        >
          <Input
            id="ajuste-cantidad"
            type="text"
            inputMode="decimal"
            className="numero"
            value={cantidad}
            onChange={(evento) => setCantidad(evento.target.value)}
            placeholder={esSaldoInicial ? '120' : '-2'}
          />
        </Field>

        {esSaldoInicial ? (
          <Field
            htmlFor="ajuste-costo"
            etiqueta="Costo unitario en unidad base"
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
            placeholder={esSaldoInicial ? 'Conteo de apertura' : 'Motivo del ajuste'}
          />
        </Field>

        {!esSaldoInicial ? (
          <div className="rounded-[6px] border border-linea px-4 py-3 text-sm">
            <p className="etiqueta">Impacto</p>
            <p className="numero mt-1 font-bold text-ink">
              {formatearCantidad(cantidadActual.aTexto())} → {formatearCantidad(resultado.aTexto())}{' '}
              {abreviarUnidad(unidad)}
            </p>
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
