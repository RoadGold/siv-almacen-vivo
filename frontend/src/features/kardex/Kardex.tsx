import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Input,
  LoadingBlock,
  Modal,
  Notice,
  Select,
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHeader,
  TableHead,
  TableRow,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import {
  abastecimientosApi,
  catalogoApi,
  inventarioApi,
  ventasApi,
} from '@/shared/api/endpoints';
import {
  etiquetaTipoMovimiento,
  formatearCantidadConSigno,
  formatearFechaHora,
  hoyISO,
  haceDiasISO,
} from '@/shared/format/formato';
import { useRetraso } from '@/shared/hooks/useRetraso';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import type { Movimiento } from '@/shared/types/api';

const TIPOS_MOVIMIENTO = [
  { valor: '', texto: 'Todos los tipos' },
  { valor: 'SALDO_INICIAL', texto: 'Saldo inicial' },
  { valor: 'ABASTECIMIENTO', texto: 'Ingreso' },
  { valor: 'VENTA', texto: 'Venta' },
  { valor: 'REVERSO_VENTA', texto: 'Anulación de venta' },
  { valor: 'REVERSO_ABASTECIMIENTO', texto: 'Anulación de ingreso' },
  { valor: 'AJUSTE_ADMINISTRATIVO', texto: 'Ajuste administrativo' },
];

const TONO_TIPO: Record<string, 'marca' | 'peligro' | 'aviso' | 'neutro'> = {
  SALDO_INICIAL: 'neutro',
  ABASTECIMIENTO: 'marca',
  VENTA: 'peligro',
  REVERSO_VENTA: 'aviso',
  REVERSO_ABASTECIMIENTO: 'aviso',
  AJUSTE_ADMINISTRATIVO: 'neutro',
};

/**
 * Pantalla KARDEX: movimiento completo del inventario con filtros y paginación
 * en el servidor (plan §5.5).
 */
export function Kardex() {
  const [productoId, setProductoId] = useState<number | null>(null);
  const [productoNombre, setProductoNombre] = useState('');
  const [tipo, setTipo] = useState('');
  const [desde, setDesde] = useState(haceDiasISO(29));
  const [hasta, setHasta] = useState(hoyISO());
  const [pagina, setPagina] = useState(1);
  const [movimiento, setMovimiento] = useState<Movimiento | null>(null);

  const filtros = useMemo(
    () => ({ producto_id: productoId, tipo: tipo || null, desde, hasta, pagina, tamano: 50 }),
    [productoId, tipo, desde, hasta, pagina],
  );

  const movimientos = useQuery({
    queryKey: ['inventario', 'kardex', filtros],
    queryFn: () => inventarioApi.movimientos(filtros),
  });

  const datos = movimientos.data;

  function cambiarFiltro(fn: () => void) {
    fn();
    setPagina(1);
  }

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="etiqueta">Explorar · Kardex</p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Kardex de movimientos</h1>
        <p className="mt-1 text-sm text-muted">
          Cada movimiento deja una traza verificable: tipo, cantidad con signo, saldo después y
          referencia de la operación que lo originó.
        </p>
      </header>

      <Card titulo="Filtros">
        <CardBody className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <label htmlFor="kardex-producto" className="mb-1 block text-sm font-semibold">
              Producto
            </label>
            <SelectorProducto
              valor={productoNombre}
              onElegir={(id, nombre) => cambiarFiltro(() => {
                setProductoId(id);
                setProductoNombre(nombre);
              })}
              onLimpiar={() => cambiarFiltro(() => {
                setProductoId(null);
                setProductoNombre('');
              })}
            />
          </div>

          <div>
            <label htmlFor="kardex-tipo" className="mb-1 block text-sm font-semibold">
              Tipo de movimiento
            </label>
            <Select
              id="kardex-tipo"
              value={tipo}
              onChange={(evento) => cambiarFiltro(() => setTipo(evento.target.value))}
            >
              {TIPOS_MOVIMIENTO.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.texto}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label htmlFor="kardex-desde" className="mb-1 block text-sm font-semibold">
              Desde
            </label>
            <Input
              id="kardex-desde"
              type="date"
              className="numero"
              value={desde}
              onChange={(evento) => cambiarFiltro(() => setDesde(evento.target.value))}
            />
          </div>

          <div>
            <label htmlFor="kardex-hasta" className="mb-1 block text-sm font-semibold">
              Hasta
            </label>
            <Input
              id="kardex-hasta"
              type="date"
              className="numero"
              value={hasta}
              onChange={(evento) => cambiarFiltro(() => setHasta(evento.target.value))}
            />
          </div>
        </CardBody>
      </Card>

      <Card titulo="Movimientos" subtitulo={`${datos?.total ?? 0} movimientos encontrados`}>
        {movimientos.isError ? (
          <div className="p-4">
            <Notice tono="error" titulo="No se pudo cargar el kardex">
              {esSinPermisos(movimientos.error)
                ? 'No tienes permiso para consultar el inventario.'
                : mensajeDeError(movimientos.error)}
            </Notice>
          </div>
        ) : movimientos.isLoading ? (
          <LoadingBlock etiqueta="Consultando movimientos…" />
        ) : (datos?.items.length ?? 0) === 0 ? (
          <EmptyState
            titulo="Sin movimientos en el periodo"
            descripcion="Amplía el rango de fechas o quita los filtros de producto y tipo."
          />
        ) : (
          <Table descripcion="Movimientos de inventario">
            <TableHead>
              <TableHeader>Fecha</TableHeader>
              <TableHeader>Tipo</TableHeader>
              <TableHeader className="text-right">Cantidad</TableHeader>
              <TableHeader className="text-right">Saldo después</TableHeader>
              <TableHeader>Referencia</TableHeader>
              <TableHeader>Usuario</TableHeader>
            </TableHead>
            <TableBody>
              {datos?.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="numero text-xs">{formatearFechaHora(item.created_at)}</TableCell>
                  <TableCell>
                    <Badge tono={TONO_TIPO[item.tipo] ?? 'neutro'}>
                      {etiquetaTipoMovimiento(item.tipo)}
                    </Badge>
                  </TableCell>
                  <TableCell numerica>
                    <span
                      className={[
                        'font-semibold',
                        item.cantidad_base_signed.startsWith('-') ? 'text-danger' : 'text-brand',
                      ].join(' ')}
                    >
                      {formatearCantidadConSigno(item.cantidad_base_signed)}
                    </span>
                  </TableCell>
                  <TableCell numerica>{formatearCantidadConSigno(item.saldo_base_despues)}</TableCell>
                  <TableCell>
                    {item.referencia ? (
                      <button
                        type="button"
                        onClick={() => setMovimiento(item)}
                        className="text-left text-sm font-semibold text-brand underline decoration-dotted underline-offset-2 hover:text-ink"
                      >
                        {item.referencia}
                      </button>
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-xs">{item.usuario ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <td className="px-3 py-2 text-xs text-muted" colSpan={5}>
                Página {datos?.pagina} de {datos?.paginas || 1} · {datos?.total ?? 0} movimientos
              </td>
              <td className="px-3 py-2">
                <div className="flex justify-end gap-2">
                  <Button
                    variante="secundario"
                    tamano="sm"
                    disabled={pagina <= 1}
                    onClick={() => setPagina((actual) => Math.max(1, actual - 1))}
                  >
                    Anterior
                  </Button>
                  <Button
                    variante="secundario"
                    tamano="sm"
                    disabled={pagina >= (datos?.paginas ?? 1)}
                    onClick={() => setPagina((actual) => actual + 1)}
                  >
                    Siguiente
                  </Button>
                </div>
              </td>
            </TableFooter>
          </Table>
        )}
      </Card>

      <ModalDetalleOperacion
        movimiento={movimiento}
        onCerrar={() => setMovimiento(null)}
      />
    </div>
  );
}

/** Buscador de producto con sugerencias del catálogo. */
function SelectorProducto({
  valor,
  onElegir,
  onLimpiar,
}: {
  valor: string;
  onElegir: (id: number, nombre: string) => void;
  onLimpiar: () => void;
}) {
  const [texto, setTexto] = useState('');
  const busquedaRetrasada = useRetraso(texto, 250);

  const productos = useQuery({
    queryKey: claves.productos.listado({ q: busquedaRetrasada, kardex: true }),
    queryFn: () =>
      catalogoApi.listarProductos({
        q: busquedaRetrasada || undefined,
        pagina: 1,
        tamano: 8,
      }),
    enabled: busquedaRetrasada.trim().length > 0,
  });

  return (
    <div className="relative">
      <div className="flex gap-2">
        <Input
          id="kardex-producto"
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          placeholder={valor || 'Nombre o código…'}
          autoComplete="off"
          aria-label="Buscar producto del kardex"
        />
        {valor ? (
          <Button variante="secundario" tamano="sm" onClick={() => { setTexto(''); onLimpiar(); }}>
            Quitar
          </Button>
        ) : null}
      </div>

      {texto.trim() && (productos.data?.items.length ?? 0) > 0 ? (
        <ul className="absolute z-20 mt-1 max-h-60 w-full overflow-y-auto rounded-[6px] border border-linea bg-surface shadow-elevado">
          {productos.data?.items.map((producto) => (
            <li key={producto.id}>
              <button
                type="button"
                onClick={() => {
                  onElegir(producto.id, producto.nombre);
                  setTexto('');
                }}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-[#faf9f5]"
              >
                <span className="font-semibold text-ink">{producto.nombre}</span>
                <span className="numero text-xs text-muted">{producto.codigo}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/** Modal con el detalle de la operación que originó el movimiento. */
function ModalDetalleOperacion({
  movimiento,
  onCerrar,
}: {
  movimiento: Movimiento | null;
  onCerrar: () => void;
}) {
  const detalle = useQuery({
    queryKey: ['operacion', movimiento?.origen_tipo, movimiento?.origen_id],
    queryFn: async () => {
      if (movimiento?.origen_tipo === 'VENTA' && movimiento.origen_id) {
        return { tipo: 'Venta' as const, operacion: await ventasApi.obtener(movimiento.origen_id) };
      }
      if (movimiento?.origen_tipo === 'ABASTECIMIENTO' && movimiento.origen_id) {
        return {
          tipo: 'Ingreso' as const,
          operacion: await abastecimientosApi.obtener(movimiento.origen_id),
        };
      }
      return null;
    },
    enabled: movimiento !== null,
  });

  const operacion = detalle.data?.operacion;

  return (
    <Modal
      abierto={movimiento !== null}
      titulo={
        movimiento?.referencia
          ? `${detalle.data?.tipo ?? 'Operación'} ${movimiento.referencia}`
          : 'Detalle de la operación'
      }
      descripcion={movimiento ? etiquetaTipoMovimiento(movimiento.tipo) : undefined}
      ancho="lg"
      onCerrar={onCerrar}
      pie={
        <Button variante="secundario" onClick={onCerrar}>
          Cerrar
        </Button>
      }
    >
      {detalle.isLoading ? (
        <LoadingBlock etiqueta="Cargando la operación…" />
      ) : detalle.isError ? (
        <Notice tono="error" titulo="No se pudo cargar la operación">
          {mensajeDeError(detalle.error)}
        </Notice>
      ) : operacion && 'numero' in operacion ? (
        <div className="flex flex-col gap-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <p className="etiqueta">Número</p>
              <p className="text-sm font-semibold text-ink">{operacion.numero}</p>
            </div>
            <div>
              <p className="etiqueta">Fecha</p>
              <p className="text-sm numero text-ink">{operacion.fecha}</p>
            </div>
            <div>
              <p className="etiqueta">Total</p>
              <p className="text-sm numero font-semibold text-ink">{operacion.total}</p>
            </div>
          </div>
          <p className="text-xs text-muted">
            {operacion.detalles.length} línea(s) · usuario: {operacion.usuario ?? '—'}
          </p>
        </div>
      ) : (
        <p className="text-sm text-muted">
          Este movimiento no tiene una operación consultable asociada. Puede corresponder a un saldo
          inicial o a un ajuste administrativo.
        </p>
      )}
    </Modal>
  );
}
