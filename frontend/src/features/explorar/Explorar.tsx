import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Input,
  LoadingBlock,
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
import { inventarioApi } from '@/shared/api/endpoints';
import {
  abreviarUnidad,
  etiquetaEstado,
  etiquetaTipoMovimiento,
  formatearCantidad,
  formatearCantidadConSigno,
  formatearFecha,
  formatearFechaHora,
  formatearMoneda,
} from '@/shared/format/formato';
import { useRetraso } from '@/shared/hooks/useRetraso';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import { PanelAjusteInventario, type ModoAjuste } from './PanelAjusteInventario';

const TONO_ESTADO = {
  agotado: 'peligro',
  bajo_minimo: 'aviso',
  disponible: 'marca',
} as const;

type Panel = 'ficha' | 'radar';

/** Pantalla EXPLORAR: existencias explicables y ficha viva del producto. */
export function Explorar() {
  const [busqueda, setBusqueda] = useState('');
  const busquedaRetrasada = useRetraso(busqueda, 250);
  const [estado, setEstado] = useState('');
  const [pagina, setPagina] = useState(1);
  const [productoId, setProductoId] = useState<number | null>(null);
  const [panel, setPanel] = useState<Panel>('radar');
  const [parametrosUrl, setParametrosUrl] = useSearchParams();
  const [modalAjuste, setModalAjuste] = useState<ModoAjuste | null>(null);
  const { puede } = useAutenticacion();
  const puedeAjustar = puede('inventario.ajustar');

  // Permite abrir la ficha de un producto desde otras pantallas (kardex, reportes).
  useEffect(() => {
    const desdeUrl = parametrosUrl.get('producto');
    if (!desdeUrl) return;
    const id = Number(desdeUrl);
    if (Number.isFinite(id) && id > 0) {
      setProductoId(id);
      setPanel('ficha');
    }
  }, [parametrosUrl]);

  const existencias = useQuery({
    queryKey: claves.existencias({
      q: busquedaRetrasada,
      estado,
      pagina,
      tamano: 25,
    }),
    queryFn: () =>
      inventarioApi.existencias({
        q: busquedaRetrasada || undefined,
        estado: estado || undefined,
        pagina,
        tamano: 25,
      }),
  });

  const radar = useQuery({
    queryKey: claves.radar,
    queryFn: () => inventarioApi.radar(20),
  });

  const ficha = useQuery({
    queryKey: claves.ficha(productoId ?? 0),
    queryFn: () => inventarioApi.ficha(productoId!),
    enabled: productoId !== null,
  });

  const datos = existencias.data;
  const totalPaginas = datos?.paginas ?? 0;

  // Un producto sin existencias puede recibir una carga de saldo inicial.
  const sinExistencias =
    (ficha.data?.existencias ?? []).every(
      (existencia) => Number(existencia.cantidad_base || '0') === 0,
    );

  function seleccionar(id: number) {
    setProductoId(id);
    setPanel('ficha');
    setParametrosUrl({ producto: String(id) }, { replace: true });
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="etiqueta">Estación · Explorar</p>
          <h1 className="mt-1 text-2xl font-bold text-ink">Explorar existencias</h1>
          <p className="mt-1 text-sm text-muted">
            Busca por nombre o código y abre la ficha viva de un producto para ver su historia.
          </p>
        </div>
        <Link
          to="/kardex"
          className="rounded-[6px] border border-linea-fuerte px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
        >
          Ver kardex completo →
        </Link>
      </header>

      <Card titulo="Filtros">
        <CardBody className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px_auto]">
          <div>
            <label htmlFor="buscador-explorar" className="mb-1 block text-sm font-semibold">
              Buscar producto
            </label>
            <Input
              id="buscador-explorar"
              value={busqueda}
              onChange={(evento) => {
                setBusqueda(evento.target.value);
                setPagina(1);
              }}
              placeholder="Nombre o código…"
              autoComplete="off"
            />
          </div>
          <div>
            <label htmlFor="filtro-estado" className="mb-1 block text-sm font-semibold">
              Estado
            </label>
            <Select
              id="filtro-estado"
              value={estado}
              onChange={(evento) => {
                setEstado(evento.target.value);
                setPagina(1);
              }}
            >
              <option value="">Todos los estados</option>
              <option value="agotado">Agotado</option>
              <option value="bajo_minimo">Bajo mínimo</option>
              <option value="disponible">Disponible</option>
            </Select>
          </div>
          <div className="flex items-end">
            <Button
              variante="secundario"
              onClick={() => {
                setBusqueda('');
                setEstado('');
                setPagina(1);
              }}
            >
              Limpiar
            </Button>
          </div>
        </CardBody>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_400px]">
        <Card titulo="Existencias" subtitulo="Selecciona una fila para abrir su ficha viva">
          {existencias.isError ? (
            <div className="p-4">
              <Notice tono="error" titulo="No se pudieron cargar las existencias">
                {esSinPermisos(existencias.error)
                  ? 'No tienes permiso para consultar el inventario.'
                  : mensajeDeError(existencias.error)}
              </Notice>
            </div>
          ) : existencias.isLoading ? (
            <LoadingBlock etiqueta="Consultando existencias…" />
          ) : (datos?.items.length ?? 0) === 0 ? (
            <EmptyState
              titulo="Sin existencias que coincidan"
              descripcion="Prueba con otro término de búsqueda o quita el filtro de estado."
            />
          ) : (
            <>
              <Table descripcion="Existencias por producto">
                <TableHead>
                  <TableHeader>Producto</TableHeader>
                  <TableHeader className="text-right">Existencia</TableHeader>
                  <TableHeader className="text-right">Mínimo</TableHeader>
                  <TableHeader className="text-right">Valor al costo</TableHeader>
                  <TableHeader>Estado</TableHeader>
                </TableHead>
                <TableBody>
                  {datos?.items.map((item) => (
                    <TableRow
                      key={item.producto_id}
                      activa={productoId === item.producto_id}
                      onClick={() => seleccionar(item.producto_id)}
                    >
                      <TableCell>
                        <span className="font-semibold text-ink">{item.producto}</span>
                        <span className="ml-2 text-xs text-muted">{item.codigo}</span>
                        {item.categoria ? (
                          <span className="ml-2 text-xs text-muted">· {item.categoria}</span>
                        ) : null}
                      </TableCell>
                      <TableCell numerica>
                        {formatearCantidad(item.cantidad_presentacion ?? item.cantidad_base)}{' '}
                        <span className="text-xs text-muted">
                          {item.presentacion_principal ?? abreviarUnidad(item.unidad_base)}
                        </span>
                      </TableCell>
                      <TableCell numerica>
                        {formatearCantidad(item.stock_minimo_base)}{' '}
                        <span className="text-xs text-muted">
                          {abreviarUnidad(item.unidad_base)}
                        </span>
                      </TableCell>
                      <TableCell numerica>{formatearMoneda(item.valor_costo)}</TableCell>
                      <TableCell>
                        <Badge tono={TONO_ESTADO[item.estado as keyof typeof TONO_ESTADO] ?? 'neutro'}>
                          {etiquetaEstado(item.estado)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                <TableFooter>
                  <td className="px-3 py-2 text-xs text-muted" colSpan={3}>
                    Página {datos?.pagina} de {totalPaginas || 1} · {datos?.total ?? 0} registros
                  </td>
                  <td className="px-3 py-2" />
                  <td className="px-3 py-2" />
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
                        disabled={pagina >= totalPaginas}
                        onClick={() => setPagina((actual) => actual + 1)}
                      >
                        Siguiente
                      </Button>
                    </div>
                  </td>
                </TableFooter>
              </Table>
            </>
          )}
        </Card>

        {/* --- Panel lateral --- */}
        <div className="flex flex-col gap-3">
          <div
            className="flex items-center gap-1 rounded-[6px] border border-linea bg-surface p-1"
            role="tablist"
            aria-label="Paneles laterales"
          >
            <button
              type="button"
              role="tab"
              aria-selected={panel === 'ficha'}
              onClick={() => setPanel('ficha')}
              className={[
                'flex-1 rounded-[4px] px-3 py-1.5 text-sm font-semibold',
                panel === 'ficha' ? 'bg-brand text-sobre-brand' : 'text-muted hover:text-brand',
              ].join(' ')}
            >
              Ficha viva
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={panel === 'radar'}
              onClick={() => setPanel('radar')}
              className={[
                'flex-1 rounded-[4px] px-3 py-1.5 text-sm font-semibold',
                panel === 'radar' ? 'bg-brand text-sobre-brand' : 'text-muted hover:text-brand',
              ].join(' ')}
            >
              Radar de reposición
            </button>
          </div>

          {panel === 'ficha' ? (
            <Card titulo="Ficha viva del producto">
              {!productoId ? (
                <EmptyState
                  titulo="Ningún producto seleccionado"
                  descripcion="Elige una fila de la tabla para ver existencias, proveedores y la huella de movimientos."
                />
              ) : ficha.isLoading ? (
                <LoadingBlock etiqueta="Cargando la ficha…" />
              ) : ficha.isError ? (
                <div className="p-4">
                  <Notice tono="error" titulo="No se pudo cargar la ficha">
                    {mensajeDeError(ficha.error)}
                  </Notice>
                </div>
              ) : ficha.data ? (
                <CardBody className="flex flex-col gap-4">
                  <div>
                    <h3 className="text-base font-semibold text-ink">{ficha.data.nombre}</h3>
                    <p className="text-xs text-muted">
                      Código {ficha.data.codigo}
                      {ficha.data.categoria ? ` · ${ficha.data.categoria}` : ''}
                      {ficha.data.marca ? ` · ${ficha.data.marca}` : ''}
                    </p>
                  </div>

                  {ficha.data.existencias.map((existencia) => (
                    <div
                      key={existencia.almacen_id}
                      className="rounded-[6px] border border-brand bg-brand-tenue px-4 py-3"
                    >
                      <p className="etiqueta">Existencia actual · {existencia.almacen}</p>
                      <p className="mt-1 text-2xl font-bold numero text-ink">
                        {formatearCantidad(existencia.cantidad_presentacion ?? existencia.cantidad_base)}{' '}
                        {existencia.presentacion_principal ?? abreviarUnidad(existencia.unidad_base)}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        En unidad base: {formatearCantidad(existencia.cantidad_base)}{' '}
                        {abreviarUnidad(existencia.unidad_base)} · costo medio{' '}
                        {formatearMoneda(existencia.costo_promedio_base)} por unidad base
                      </p>
                    </div>
                  ))}

                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <dt className="etiqueta">Último costo</dt>
                      <dd className="numero text-ink">
                        {ficha.data.ultimo_costo
                          ? formatearMoneda(ficha.data.ultimo_costo)
                          : 'Sin registro'}
                      </dd>
                    </div>
                    <div>
                      <dt className="etiqueta">Stock mínimo</dt>
                      <dd className="numero text-ink">
                        {formatearCantidad(ficha.data.stock_minimo_base)}{' '}
                        {abreviarUnidad(ficha.data.unidad_base)}
                      </dd>
                    </div>
                  </dl>

                  {puedeAjustar ? (
                    <section className="border-t border-linea pt-3">
                      <h4 className="etiqueta mb-2">Acciones administrativas</h4>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variante="secundario"
                          onClick={() => setModalAjuste('ajuste')}
                        >
                          Registrar ajuste
                        </Button>
                        {sinExistencias ? (
                          <Button
                            variante="secundario"
                            onClick={() => setModalAjuste('saldo-inicial')}
                          >
                            Cargar saldo inicial
                          </Button>
                        ) : null}
                      </div>
                      <p className="mt-2 text-xs text-muted">
                        Los ajustes y las cargas iniciales se registran con motivo, usuario y fecha.
                        No existe un botón para «editar el stock».
                      </p>
                    </section>
                  ) : null}

                  <section>
                    <h4 className="etiqueta mb-1">Precios por presentación</h4>
                    <ul className="divide-y divide-linea text-sm">
                      {ficha.data.presentaciones
                        .filter((item) => item.activo)
                        .map((item) => (
                          <li key={item.id} className="flex items-center justify-between py-1.5">
                            <span className="text-ink">
                              {item.nombre}
                              <span className="ml-2 text-xs text-muted">
                                1 = {formatearCantidad(item.factor_base)}{' '}
                                {abreviarUnidad(ficha.data.unidad_base)}
                              </span>
                            </span>
                            <span className="numero text-ink">{formatearMoneda(item.precio_venta)}</span>
                          </li>
                        ))}
                    </ul>
                  </section>

                  <section>
                    <h4 className="etiqueta mb-1">Proveedores conocidos</h4>
                    {ficha.data.proveedores.length === 0 ? (
                      <p className="text-sm text-muted">
                        Este producto todavía no tiene proveedores vinculados.
                      </p>
                    ) : (
                      <ul className="divide-y divide-linea text-sm">
                        {ficha.data.proveedores.map((proveedor) => (
                          <li key={proveedor.proveedor_id} className="flex items-center justify-between py-1.5">
                            <span className="text-ink">
                              {proveedor.proveedor}
                              {proveedor.habitual ? (
                                <Badge tono="marca" className="ml-2">
                                  Habitual
                                </Badge>
                              ) : null}
                            </span>
                            <span className="text-xs text-muted">
                              {proveedor.ultima_fecha_compra
                                ? `Última compra ${formatearFecha(proveedor.ultima_fecha_compra)}`
                                : 'Sin compras'}
                              {proveedor.ultimo_costo
                                ? ` · ${formatearMoneda(proveedor.ultimo_costo)}`
                                : ''}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>

                  <section>
                    <h4 className="etiqueta mb-1">Huella del producto</h4>
                    {ficha.data.movimientos_recientes.length === 0 ? (
                      <p className="text-sm text-muted">Este producto todavía no tiene movimientos.</p>
                    ) : (
                      <ol className="space-y-2">
                        {ficha.data.movimientos_recientes.map((movimiento) => (
                          <li
                            key={movimiento.id}
                            className="border-l-2 border-linea-fuerte pl-3 text-sm"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-semibold text-ink">
                                {etiquetaTipoMovimiento(movimiento.tipo)}
                              </span>
                              <span
                                className={[
                                  'numero font-semibold',
                                  movimiento.cantidad_base_signed.startsWith('-')
                                    ? 'text-danger'
                                    : 'text-brand',
                                ].join(' ')}
                              >
                                {formatearCantidadConSigno(movimiento.cantidad_base_signed)}
                              </span>
                            </div>
                            <p className="text-xs text-muted">
                              Saldo: {formatearCantidad(movimiento.saldo_base_despues)}{' '}
                              {abreviarUnidad(ficha.data.unidad_base)}
                              {movimiento.referencia ? ` · ${movimiento.referencia}` : ''}
                              {movimiento.usuario ? ` · ${movimiento.usuario}` : ''}
                              {movimiento.created_at
                                ? ` · ${formatearFechaHora(movimiento.created_at)}`
                                : ''}
                            </p>
                          </li>
                        ))}
                      </ol>
                    )}
                  </section>
                </CardBody>
              ) : null}
            </Card>
          ) : (
            <Card titulo="Radar de reposición" subtitulo="Ordenado por urgencia">
              {radar.isLoading ? (
                <LoadingBlock etiqueta="Calculando prioridades…" />
              ) : radar.isError ? (
                <div className="p-4">
                  <Notice tono="error" titulo="No se pudo calcular el radar">
                    {mensajeDeError(radar.error)}
                  </Notice>
                </div>
              ) : (radar.data?.length ?? 0) === 0 ? (
                <EmptyState
                  titulo="Nada que reponer"
                  descripcion="Ningún producto está agotado ni por debajo del stock mínimo."
                />
              ) : (
                <ul className="divide-y divide-linea">
                  {radar.data?.map((item) => (
                    <li key={item.producto_id} className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => seleccionar(item.producto_id)}
                        className="w-full text-left"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-semibold text-ink">{item.producto}</span>
                          <Badge tono={TONO_ESTADO[item.estado as keyof typeof TONO_ESTADO] ?? 'neutro'}>
                            {item.estado === 'agotado' ? 'Agotado · urgente' : 'Bajo mínimo'}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted">
                          Quedan {formatearCantidad(item.cantidad_presentacion ?? item.cantidad_base)}{' '}
                          {item.presentacion_principal ?? abreviarUnidad(item.unidad_base)} · mínimo{' '}
                          {formatearCantidad(item.stock_minimo_base)}{' '}
                          {abreviarUnidad(item.unidad_base)}
                        </p>
                        <p className="mt-1 text-xs text-ink-suave">
                          Proveedor sugerido: {item.proveedor_sugerido ?? 'sin proveedor vinculado'}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}
        </div>
      </div>

      <PanelAjusteInventario
        abierto={modalAjuste !== null}
        onCerrar={() => setModalAjuste(null)}
        modo={modalAjuste ?? 'ajuste'}
        producto={
          ficha.data
            ? {
                id: ficha.data.id,
                nombre: ficha.data.nombre,
                codigo: ficha.data.codigo,
                unidad_base: ficha.data.unidad_base ?? null,
              }
            : null
        }
        almacenId={ficha.data?.existencias?.[0]?.almacen_id ?? null}
        existenciaBase={ficha.data?.existencias?.[0]?.cantidad_base ?? '0'}
      />
    </div>
  );
}
