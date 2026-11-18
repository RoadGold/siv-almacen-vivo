/**
 * Historial de ventas: consulta, detalle, reimpresión del ticket y anulación.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Field,
  Input,
  LoadingBlock,
  Modal,
  Notice,
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
  useToast,
} from '@/design-system';
import { ventasApi } from '@/shared/api/endpoints';
import { formatearCantidad, formatearFecha, formatearMoneda } from '@/shared/format/formato';
import { mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import type { Venta } from '@/shared/types/api';

const TONO_ESTADO: Record<string, 'marca' | 'aviso' | 'peligro' | 'neutro'> = {
  CONFIRMADO: 'marca',
  ANULADO: 'peligro',
  REVERTIDO: 'peligro',
  BORRADOR: 'neutro',
};

export function Ventas() {
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [estado, setEstado] = useState('');
  const [pagina, setPagina] = useState(1);
  const [detalle, setDetalle] = useState<Venta | null>(null);
  const [modalAnular, setModalAnular] = useState<Venta | null>(null);
  const [motivo, setMotivo] = useState('');
  const [impresion, setImpresion] = useState<string | null>(null);

  const cliente = useQueryClient();
  const { notificar } = useToast();

  const consulta = useQuery({
    queryKey: ['ventas', 'listado', { desde, hasta, estado, pagina }],
    queryFn: () =>
      ventasApi.listar({
        desde: desde || undefined,
        hasta: hasta || undefined,
        estado: estado || undefined,
        pagina,
        tamano: 20,
      }),
  });

  const imprimir = useMutation({
    mutationFn: (id: number) => ventasApi.imprimir(id),
    onSuccess: (resultado) => {
      setImpresion(resultado.mensaje);
      notificar(resultado.mensaje, 'exito');
      cliente.invalidateQueries({ queryKey: ['ventas'] });
    },
    onError: (error) => {
      setImpresion(mensajeDeError(error));
      notificar(mensajeDeError(error), 'error');
    },
  });

  const anular = useMutation({
    mutationFn: (datos: { id: number; motivo: string }) =>
      ventasApi.anular(datos.id, datos.motivo),
    onSuccess: (venta) => {
      notificar(`Venta ${venta.numero} anulada.`, 'exito');
      setModalAnular(null);
      setMotivo('');
      setDetalle(null);
      registrarOperacion(`Anulación de venta ${venta.numero}`);
      cliente.invalidateQueries({ queryKey: ['ventas'] });
      cliente.invalidateQueries({ queryKey: ['inventario'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const datos = consulta.data;
  const items = datos?.items ?? [];

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="etiqueta">Ventas</p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Historial de ventas</h1>
        <p className="mt-1 text-sm text-muted">
          Consulta las ventas registradas, reimprime el ticket o anula una venta con autorización.
        </p>
      </header>

      <Card titulo="Filtros">
        <CardBody className="flex flex-wrap items-end gap-3">
          <div className="w-[150px]">
            <Field
              htmlFor="ventas-desde"
              etiqueta="Desde"
              ayuda="El navegador muestra la fecha como dd/mm/aaaa."
            >
              <Input
                id="ventas-desde"
                type="date"
                value={desde}
                onChange={(evento) => {
                  setDesde(evento.target.value);
                  setPagina(1);
                }}
              />
            </Field>
          </div>
          <div className="w-[150px]">
            <Field
              htmlFor="ventas-hasta"
              etiqueta="Hasta"
              ayuda="El navegador muestra la fecha como dd/mm/aaaa."
            >
              <Input
                id="ventas-hasta"
                type="date"
                value={hasta}
                onChange={(evento) => {
                  setHasta(evento.target.value);
                  setPagina(1);
                }}
              />
            </Field>
          </div>
          <div className="w-[170px]">
            <Field
              htmlFor="ventas-estado"
              etiqueta="Estado"
              ayuda="Ejemplo: Confirmadas o Anuladas."
            >
              <select
                id="ventas-estado"
                value={estado}
                onChange={(evento) => {
                  setEstado(evento.target.value);
                  setPagina(1);
                }}
                className="w-full rounded-[6px] border border-linea bg-surface px-2 py-1.5 text-sm text-ink"
              >
                <option value="">Todas</option>
                <option value="CONFIRMADO">Confirmadas</option>
                <option value="ANULADO">Anuladas</option>
              </select>
            </Field>
          </div>
          <p className="pb-1 text-xs text-muted">
            {datos ? `${datos.total} venta(s) encontrada(s)` : ''}
          </p>
        </CardBody>
      </Card>

      {impresion ? (
        <Notice tono="info" titulo="Impresión">
          {impresion}
        </Notice>
      ) : null}

      <Card titulo="Ventas registradas">
        {consulta.isLoading ? (
          <LoadingBlock etiqueta="Cargando ventas…" />
        ) : consulta.isError ? (
          <div className="p-4">
            <Notice tono="error" titulo="No se pudieron cargar las ventas">
              {mensajeDeError(consulta.error)}
            </Notice>
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            titulo="No hay ventas en este periodo"
            descripcion="Ajuste los filtros o registre una venta desde la estación Vender."
          />
        ) : (
          <>
            <Table descripcion="Ventas registradas">
              <TableHead>
                <TableHeader>Número</TableHeader>
                <TableHeader>Fecha</TableHeader>
                <TableHeader>Cajero</TableHeader>
                <TableHeader>Estado</TableHeader>
                <TableHeader>Ticket</TableHeader>
                <TableHeader className="text-right">Total</TableHeader>
                <TableHeader>Acciones</TableHeader>
              </TableHead>
              <TableBody>
                {items.map((venta) => (
                  <TableRow key={venta.id}>
                    <TableCell className="numero font-semibold">{venta.numero}</TableCell>
                    <TableCell>{formatearFecha(venta.fecha)}</TableCell>
                    <TableCell>{venta.usuario ?? '—'}</TableCell>
                    <TableCell>
                      <Badge tono={TONO_ESTADO[venta.estado] ?? 'neutro'}>
                        {venta.estado === 'CONFIRMADO'
                          ? 'Confirmada'
                          : venta.estado === 'ANULADO'
                            ? 'Anulada'
                            : venta.estado}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {venta.ticket_impreso ? (
                        <Badge tono="marca">Impreso</Badge>
                      ) : venta.impresion_error ? (
                        <Badge tono="peligro">Pendiente</Badge>
                      ) : (
                        <span className="text-xs text-muted">—</span>
                      )}
                    </TableCell>
                    <TableCell numerica className="font-semibold">
                      {formatearMoneda(venta.total)}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variante="fantasma"
                          tamano="sm"
                          onClick={() => setDetalle(venta)}
                        >
                          Ver
                        </Button>
                        {venta.estado === 'CONFIRMADO' ? (
                          <Button
                            variante="fantasma"
                            tamano="sm"
                            disabled={imprimir.isPending}
                            onClick={() => imprimir.mutate(venta.id)}
                          >
                            {venta.ticket_impreso ? 'Reimprimir' : 'Imprimir'}
                          </Button>
                        ) : null}
                        {venta.estado === 'CONFIRMADO' ? (
                          <Button
                            variante="fantasma"
                            tamano="sm"
                            onClick={() => setModalAnular(venta)}
                          >
                            Anular
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              {datos && datos.paginas > 1 ? (
                <TableFooter>
                  <TableRow>
                    <TableCell className="text-xs text-muted">
                      Página {datos.pagina} de {datos.paginas}
                    </TableCell>
                  </TableRow>
                </TableFooter>
              ) : null}
            </Table>

            {datos && datos.paginas > 1 ? (
              <div className="flex items-center justify-end gap-2 px-4 py-3">
                <Button
                  variante="secundario"
                  tamano="sm"
                  disabled={pagina <= 1}
                  onClick={() => setPagina((valor) => Math.max(1, valor - 1))}
                >
                  Anterior
                </Button>
                <Button
                  variante="secundario"
                  tamano="sm"
                  disabled={pagina >= datos.paginas}
                  onClick={() => setPagina((valor) => valor + 1)}
                >
                  Siguiente
                </Button>
              </div>
            ) : null}
          </>
        )}
      </Card>

      {/* --- Detalle de la venta --- */}
      <Modal
        abierto={detalle !== null}
        titulo={detalle ? `Venta ${detalle.numero}` : 'Detalle de la venta'}
        descripcion={
          detalle
            ? `${formatearFecha(detalle.fecha)} · ${detalle.usuario ?? 'sistema'}`
            : undefined
        }
        ancho="lg"
        onCerrar={() => setDetalle(null)}
        pie={
          detalle && detalle.estado === 'CONFIRMADO' ? (
            <>
              <Button
                variante="secundario"
                disabled={imprimir.isPending}
                onClick={() => imprimir.mutate(detalle.id)}
              >
                {detalle.ticket_impreso ? 'Reimprimir ticket' : 'Imprimir ticket'}
              </Button>
              <Button variante="primario" onClick={() => setModalAnular(detalle)}>
                Anular venta
              </Button>
            </>
          ) : undefined
        }
      >
        {detalle ? (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-6">
              <div>
                <p className="etiqueta">Total</p>
                <p className="text-2xl font-bold numero text-ink">
                  {formatearMoneda(detalle.total)}
                </p>
              </div>
              {detalle.forma_pago ? (
                <div>
                  <p className="etiqueta">Pago</p>
                  <p className="text-lg font-semibold text-ink">
                    {detalle.forma_pago}
                    {detalle.monto_recibido
                      ? ` · recibido ${formatearMoneda(detalle.monto_recibido)}`
                      : ''}
                    {detalle.vuelto ? ` · vuelto ${formatearMoneda(detalle.vuelto)}` : ''}
                  </p>
                </div>
              ) : null}
              <div>
                <p className="etiqueta">Ticket</p>
                <p className="text-sm text-ink">
                  {detalle.ticket_impreso
                    ? `Impreso${detalle.impreso_at ? ` el ${formatearFecha(detalle.impreso_at)}` : ''}`
                    : (detalle.impresion_error ?? 'Pendiente de impresión')}
                </p>
              </div>
            </div>

            <Table descripcion="Líneas de la venta">
              <TableHead>
                <TableHeader>Producto</TableHeader>
                <TableHeader className="text-right">Cantidad</TableHeader>
                <TableHeader className="text-right">Precio</TableHeader>
                <TableHeader className="text-right">Subtotal</TableHeader>
              </TableHead>
              <TableBody>
                {detalle.detalles.map((linea) => (
                  <TableRow key={linea.id}>
                    <TableCell>
                      {linea.producto_nombre}
                      {linea.presentacion_nombre ? (
                        <span className="text-xs text-muted"> · {linea.presentacion_nombre}</span>
                      ) : null}
                      {linea.precio_original !== linea.precio_unitario ? (
                        <span className="ml-2">
                          <Badge tono="aviso">Precio modificado</Badge>
                          {linea.motivo_precio ? (
                            <span className="ml-1 text-xs text-muted">{linea.motivo_precio}</span>
                          ) : null}
                        </span>
                      ) : null}
                    </TableCell>
                    <TableCell numerica>
                      {formatearCantidad(linea.cantidad)} {linea.presentacion_nombre ?? ''}
                    </TableCell>
                    <TableCell numerica>
                      {formatearMoneda(linea.precio_unitario)}
                      {linea.precio_original !== linea.precio_unitario ? (
                        <span className="ml-1 text-xs text-muted line-through">
                          {formatearMoneda(linea.precio_original)}
                        </span>
                      ) : null}
                    </TableCell>
                    <TableCell numerica className="font-semibold">
                      {formatearMoneda(linea.subtotal)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </Modal>

      {/* --- Anulación --- */}
      <Modal
        abierto={modalAnular !== null}
        titulo="Anular venta"
        descripcion={
          modalAnular
            ? `La venta ${modalAnular.numero} quedará registrada como anulada y el stock volverá a entrar.`
            : undefined
        }
        onCerrar={() => {
          setModalAnular(null);
          setMotivo('');
        }}
        pie={
          <>
            <Button
              variante="secundario"
              onClick={() => {
                setModalAnular(null);
                setMotivo('');
              }}
            >
              Cancelar
            </Button>
            <Button
              variante="primario"
              disabled={motivo.trim().length < 5 || anular.isPending}
              cargando={anular.isPending}
              textoCargando="Anulando…"
              onClick={() => {
                if (modalAnular) {
                  anular.mutate({ id: modalAnular.id, motivo: motivo.trim() });
                }
              }}
            >
              Anular venta
            </Button>
          </>
        }
      >
        <Field
          htmlFor="motivo-anulacion"
          etiqueta="Motivo de la anulación"
          ejemplo="Error de digitación en la caja"
          ayuda="Obligatorio (mínimo 5 caracteres). Queda registrado en la auditoría."
        >
          <Textarea
            id="motivo-anulacion"
            value={motivo}
            onChange={(evento) => setMotivo(evento.target.value)}
          />
        </Field>
      </Modal>
    </div>
  );
}
