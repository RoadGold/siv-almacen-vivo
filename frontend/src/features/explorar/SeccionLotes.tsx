/**
 * Sección «Lotes» de la ficha del producto.
 *
 * Cada lote es una porción de existencias con su propio costo y su propio
 * precio de venta. La sección permite consultar sus datos y, si el usuario
 * tiene el permiso `precios.gestionar`, corregir el precio de venta de una
 * presentación dentro del lote (queda auditado por el backend).
 */

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Field,
  Input,
  Modal,
  Notice,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHead,
  TableRow,
  useToast,
} from '@/design-system';
import { lotesApi } from '@/shared/api/endpoints';
import { Decimal } from '@/shared/format/decimal';
import { reglaDe } from '@/shared/contrato/reglas';
import {
  abreviarUnidad,
  formatearCantidad,
  formatearFecha,
  formatearMoneda,
} from '@/shared/format/formato';
import { mensajeDeError } from '@/shared/hooks/errores';
import type { LoteResumen, Presentacion } from '@/shared/types/api';

interface Props {
  productoId: number;
  lotes: LoteResumen[];
  cargando: boolean;
  error: unknown;
  /** `true` si el usuario puede administrar los precios de venta. */
  puedeEditarPrecios: boolean;
  /** Presentaciones del producto (respaldo cuando el lote aún no tiene precios). */
  presentaciones: Presentacion[];
  unidadBase?: string | null;
}

interface OpcionPrecio {
  id: number;
  nombre: string;
  precio: string;
}

/** Etiqueta y tono del estado de un lote (el color nunca va solo). */
export function estadoLote(lote: LoteResumen): { texto: string; tono: 'marca' | 'peligro' | 'neutro' } {
  if (lote.estado === 'AGOTADO') return { texto: 'Agotado', tono: 'peligro' };
  if (lote.estado === 'INHABILITADO') return { texto: 'Inhabilitado', tono: 'neutro' };
  return { texto: 'Disponible', tono: 'marca' };
}

export function SeccionLotes({
  productoId,
  lotes,
  cargando,
  error,
  puedeEditarPrecios,
  presentaciones,
  unidadBase,
}: Props) {
  const [loteEnEdicion, setLoteEnEdicion] = useState<LoteResumen | null>(null);
  const [presentacionId, setPresentacionId] = useState<number | ''>('');
  const [precio, setPrecio] = useState('0');
  const [motivo, setMotivo] = useState('');
  const [errorForm, setErrorForm] = useState<string | null>(null);

  const cliente = useQueryClient();
  const { notificar } = useToast();

  /** Precios disponibles del lote; si no tiene, se ofrecen las presentaciones del producto. */
  const opcionesPrecio = useMemo<OpcionPrecio[]>(() => {
    if (!loteEnEdicion) return [];
    if (loteEnEdicion.precios.length > 0) {
      return loteEnEdicion.precios.map((item) => ({
        id: item.presentacion_id,
        nombre: item.presentacion_nombre || `Presentación #${item.presentacion_id}`,
        precio: item.precio,
      }));
    }
    return presentaciones
      .filter((item) => item.activo && item.es_venta)
      .map((item) => ({ id: item.id, nombre: item.nombre, precio: item.precio_venta }));
  }, [loteEnEdicion, presentaciones]);

  // Al abrir el modal se precarga la primera presentación y su precio actual.
  useEffect(() => {
    if (!loteEnEdicion) return;
    const primera = opcionesPrecio[0];
    setPresentacionId(primera?.id ?? '');
    setPrecio(primera?.precio ?? '0');
    setMotivo('');
    setErrorForm(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteEnEdicion?.id]);

  function cambiarPresentacion(id: number) {
    setPresentacionId(id);
    const opcion = opcionesPrecio.find((item) => item.id === id);
    setPrecio(opcion?.precio ?? '0');
  }

  const guardar = useMutation({
    mutationFn: () => {
      if (!loteEnEdicion) throw new Error('Seleccione un lote.');
      if (presentacionId === '') throw new Error('Seleccione la presentación a modificar.');
      // Las mismas reglas que aplica el backend (ver `PrecioLoteIn`).
      const valor = Decimal.intentarDesde(precio);
      if (valor === null) throw new Error('El precio debe ser un número.');
      if (valor.comparar(0) < 0) throw new Error('El precio no puede ser negativo.');
      if (motivo.trim().length > (reglaDe('lotes_precio', 'motivo').max ?? 200)) {
        throw new Error('El motivo no puede pasar de 200 caracteres.');
      }
      return lotesApi.actualizarPrecio(loteEnEdicion.id, {
        presentacion_id: presentacionId,
        precio: valor.aTexto(),
        motivo: motivo.trim() || undefined,
      });
    },
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ['lotes', productoId] });
      cliente.invalidateQueries({ queryKey: ['inventario', 'ficha', productoId] });
      notificar('Precio del lote actualizado.', 'exito');
      setLoteEnEdicion(null);
    },
    onError: (fallo) => setErrorForm(mensajeDeError(fallo)),
  });

  if (cargando) {
    return (
      <section>
        <h4 className="etiqueta mb-1">Lotes</h4>
        <p className="text-sm text-muted">Cargando lotes del producto…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <h4 className="etiqueta mb-1">Lotes</h4>
        <Notice tono="error" titulo="No se pudieron cargar los lotes">
          {mensajeDeError(error)}
        </Notice>
      </section>
    );
  }

  if (lotes.length === 0) {
    return (
      <section>
        <h4 className="etiqueta mb-1">Lotes</h4>
        <p className="text-sm text-muted">
          Este producto todavía no tiene lotes. Los lotes se crean al recibir mercadería: cada
          línea de ingreso genera un lote con su propio stock, costo y precio de venta.
        </p>
      </section>
    );
  }

  return (
    <section>
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <h4 className="etiqueta">Lotes</h4>
        <span className="text-xs text-muted">{lotes.length} lote(s)</span>
      </div>

      <Table descripcion="Lotes de inventario del producto">
        <TableHead>
          <TableHeader>Lote</TableHeader>
          <TableHeader>Fecha</TableHeader>
          <TableHeader className="text-right">Stock</TableHeader>
          <TableHeader className="text-right">Costo</TableHeader>
          <TableHeader className="text-right">Precio</TableHeader>
          <TableHeader>Estado</TableHeader>
        </TableHead>
        <TableBody>
          {lotes.map((lote) => {
            const estado = estadoLote(lote);
            const puedeEditar =
              puedeEditarPrecios &&
              (lote.precios.length > 0 ||
                presentaciones.some((item) => item.activo && item.es_venta));
            return (
              <TableRow key={lote.id}>
                <TableCell>
                  <span className="numero text-xs font-semibold text-ink">{lote.codigo_lote}</span>
                  {puedeEditar ? (
                    <button
                      type="button"
                      onClick={() => setLoteEnEdicion(lote)}
                      className="mt-0.5 block text-left text-2xs font-semibold text-brand underline decoration-dotted underline-offset-2 hover:text-ink"
                    >
                      Editar precio del lote
                    </button>
                  ) : null}
                </TableCell>
                <TableCell className="numero text-xs">
                  {lote.fecha_ingreso ? formatearFecha(lote.fecha_ingreso) : '—'}
                </TableCell>
                <TableCell numerica>
                  {formatearCantidad(lote.cantidad_disponible)}{' '}
                  <span className="text-xs text-muted">{abreviarUnidad(unidadBase)}</span>
                </TableCell>
                <TableCell numerica>
                  {formatearMoneda(lote.costo_base)}
                  <span className="block text-2xs text-muted">por unidad base</span>
                </TableCell>
                <TableCell numerica>
                  {formatearMoneda(lote.precio_venta)}
                  {lote.tiene_precios_distintos ? (
                    <span className="block text-2xs text-muted">
                      entre {formatearMoneda(lote.precio_minimo ?? '0')} y{' '}
                      {formatearMoneda(lote.precio_maximo ?? '0')}
                    </span>
                  ) : null}
                </TableCell>
                <TableCell>
                  <Badge tono={estado.tono}>{estado.texto}</Badge>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <Modal
        abierto={loteEnEdicion !== null}
        titulo="Editar precio del lote"
        descripcion={
          loteEnEdicion
            ? `${loteEnEdicion.codigo_lote} · stock ${formatearCantidad(
                loteEnEdicion.cantidad_disponible,
              )} ${abreviarUnidad(unidadBase)}`
            : undefined
        }
        onCerrar={() => setLoteEnEdicion(null)}
        pie={
          <>
            <Button variante="secundario" onClick={() => setLoteEnEdicion(null)}>
              Cancelar
            </Button>
            <Button
              variante="primario"
              cargando={guardar.isPending}
              textoCargando="Guardando…"
              disabled={presentacionId === ''}
              onClick={() => {
                setErrorForm(null);
                guardar.mutate();
              }}
            >
              Guardar precio
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {errorForm ? (
            <Notice tono="error" titulo="No se pudo actualizar el precio">
              {errorForm}
            </Notice>
          ) : null}

          <Notice tono="info" titulo="Cambio de precio por lote">
            El precio nuevo solo afecta a este lote. Queda registrado con tu usuario, la fecha y el
            motivo.
          </Notice>

          <Field
            htmlFor="lote-precio-presentacion"
            etiqueta="Presentación"
            ayuda="El precio se guarda por presentación dentro del lote. Ejemplo: Saco 50 kg."
          >
            <Select
              id="lote-precio-presentacion"
              value={presentacionId}
              onChange={(evento) => cambiarPresentacion(Number(evento.target.value))}
            >
              {opcionesPrecio.map((opcion) => (
                <option key={opcion.id} value={opcion.id}>
                  {opcion.nombre} · {formatearMoneda(opcion.precio)}
                </option>
              ))}
            </Select>
          </Field>

          <Field
            htmlFor="lote-precio-nuevo"
            etiqueta="Precio de venta"
            ejemplo="13.50"
            ayuda="Precio por unidad de la presentación (no por kilo)."
          >
            <Input
              id="lote-precio-nuevo"
              className="numero"
              inputMode="decimal"
              prefijo="S/"
              value={precio}
              onChange={(evento) => setPrecio(evento.target.value)}
            />
          </Field>

          <Field
            htmlFor="lote-precio-motivo"
            etiqueta="Motivo"
            ejemplo="Motivo del cambio"
            ayuda="Opcional. Por ejemplo: «Ajuste por promoción de temporada»."
          >
            <Input
              id="lote-precio-motivo"
              value={motivo}
              onChange={(evento) => setMotivo(evento.target.value)}
            />
          </Field>
        </div>
      </Modal>
    </section>
  );
}
