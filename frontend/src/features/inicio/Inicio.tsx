import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Badge,
  Card,
  CardBody,
  EmptyState,
  LoadingBlock,
  Notice,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import { abastecimientosApi, dashboardApi, ventasApi } from '@/shared/api/endpoints';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import {
  etiquetaEstadoOperacion,
  formatearFechaHora,
  formatearMoneda,
  formatearNumero,
} from '@/shared/format/formato';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';

/** Saludo según la hora local del equipo. */
function saludo(): string {
  const hora = new Date().getHours();
  if (hora < 12) return 'Buenos días';
  if (hora < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

const ESTACIONES = [
  {
    titulo: 'Vender',
    descripcion: 'Registrar una venta y ver el impacto en el stock al instante.',
    ruta: '/vender',
    permiso: 'ventas.crear',
    accion: 'Nueva venta →',
  },
  {
    titulo: 'Recibir',
    descripcion: 'Registrar la mercadería que llegó de un proveedor.',
    ruta: '/recibir',
    permiso: 'abastecimientos.crear',
    accion: 'Nuevo ingreso →',
  },
  {
    titulo: 'Explorar',
    descripcion: 'Buscar existencias, revisar la ficha de un producto y su historia.',
    ruta: '/explorar',
    permiso: 'inventario.ver',
    accion: 'Buscar stock →',
  },
];

/** Pantalla de inicio orientada a tareas (plan §2.3). */
export function Inicio() {
  const { usuario, puede } = useAutenticacion();

  const resumen = useQuery({
    queryKey: claves.resumen,
    queryFn: () => dashboardApi.resumen(),
  });

  const ventas = useQuery({
    queryKey: claves.ventas.listado({ recientes: true }),
    queryFn: () => ventasApi.listar({ pagina: 1, tamano: 4 }),
    enabled: puede('ventas.ver'),
  });

  const ingresos = useQuery({
    queryKey: claves.abastecimientos.listado({ recientes: true }),
    queryFn: () => abastecimientosApi.listar({ pagina: 1, tamano: 4 }),
    enabled: puede('abastecimientos.ver'),
  });

  const estacionesVisibles = ESTACIONES.filter((estacion) => !estacion.permiso || puede(estacion.permiso));

  return (
    <div className="flex flex-col gap-6">
      <section>
        <p className="etiqueta">Inicio</p>
        <h1 className="mt-1 text-2xl font-bold text-ink">
          {saludo()}, {usuario?.nombre.split(' ')[0] ?? ''}. ¿Qué necesitas hacer?
        </h1>
        <p className="mt-1 text-sm text-muted">
          Elige una estación de trabajo. Cada una explica qué va a cambiar antes de confirmar.
        </p>
      </section>

      {resumen.isError ? (
        <Notice tono="error" titulo="No se pudo cargar el resumen del día">
          {mensajeDeError(resumen.error)}
        </Notice>
      ) : null}

      <section aria-label="Estaciones de trabajo" className="grid gap-4 md:grid-cols-3">
        {estacionesVisibles.map((estacion) => (
          <Link
            key={estacion.ruta}
            to={estacion.ruta}
            className="group flex flex-col justify-between gap-6 rounded-tarjeta border border-linea bg-surface p-5 shadow-panel transition-colors hover:border-brand"
          >
            <div>
              <p className="etiqueta">{estacion.accion.replace(' →', '')}</p>
              <h2 className="mt-1 text-xl font-bold uppercase tracking-[0.12em] text-ink group-hover:text-brand">
                {estacion.titulo}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">{estacion.descripcion}</p>
            </div>
            <span className="text-sm font-semibold text-brand">Entrar →</span>
          </Link>
        ))}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card titulo="Hoy en la tienda" subtitulo="Ventas confirmadas del día en curso">
          {resumen.isLoading ? (
            <LoadingBlock etiqueta="Consultando el resumen…" />
          ) : resumen.data ? (
            <CardBody className="grid gap-4 sm:grid-cols-3">
              <div>
                <p className="etiqueta">Ventas del día</p>
                <p className="mt-1 text-2xl font-bold numero text-ink">
                  {formatearMoneda(resumen.data.ventas_dia)}
                </p>
              </div>
              <div>
                <p className="etiqueta">Operaciones</p>
                <p className="mt-1 text-2xl font-bold numero text-ink">
                  {formatearNumero(resumen.data.cantidad_ventas_dia, 0)}
                </p>
              </div>
              <div>
                <p className="etiqueta">Valor del inventario (costo)</p>
                <p className="mt-1 text-2xl font-bold numero text-ink">
                  {formatearMoneda(resumen.data.valor_inventario_costo)}
                </p>
              </div>
              <p className="text-xs text-muted sm:col-span-3">
                Fecha del resumen: {resumen.data.fecha} · Productos activos en catálogo:{' '}
                {formatearNumero(resumen.data.total_productos, 0)}
              </p>
            </CardBody>
          ) : null}
        </Card>

        <Card titulo="Atención necesaria" subtitulo="Productos que requieren reposición">
          {resumen.isLoading ? (
            <LoadingBlock etiqueta="Consultando el resumen…" />
          ) : resumen.data ? (
            <CardBody className="flex flex-col gap-3">
              <div className="flex items-center justify-between rounded-[6px] border border-danger bg-danger-tenue px-4 py-3">
                <div>
                  <p className="text-sm font-semibold text-ink">Agotados</p>
                  <p className="text-xs text-muted">Sin existencias: no se pueden vender.</p>
                </div>
                <p className="text-2xl font-bold numero text-ink">
                  {formatearNumero(resumen.data.productos_agotados, 0)}
                </p>
              </div>
              <div className="flex items-center justify-between rounded-[6px] border border-warning bg-warning-tenue px-4 py-3">
                <div>
                  <p className="text-sm font-semibold text-ink">Bajo mínimo</p>
                  <p className="text-xs text-muted">Por debajo del stock mínimo configurado.</p>
                </div>
                <p className="text-2xl font-bold numero text-ink">
                  {formatearNumero(resumen.data.productos_bajo_minimo, 0)}
                </p>
              </div>
              <Link
                to="/explorar"
                className="self-start rounded-[6px] border border-linea-fuerte px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
              >
                Ver radar de reposición
              </Link>
            </CardBody>
          ) : null}
        </Card>
      </div>

      <Card titulo="Actividad reciente" subtitulo="Últimas ventas y últimos ingresos confirmados">
        <CardBody className="grid gap-6 lg:grid-cols-2">
          <section>
            <h3 className="etiqueta mb-2">Ventas</h3>
            {ventas.isLoading ? (
              <LoadingBlock etiqueta="Cargando ventas…" />
            ) : ventas.isError ? (
              <Notice tono="error" titulo="No se pudieron cargar las ventas">
                {esSinPermisos(ventas.error)
                  ? 'No tienes permiso para consultar el historial de ventas.'
                  : mensajeDeError(ventas.error)}
              </Notice>
            ) : (ventas.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                titulo="Todavía no hay ventas registradas"
                descripcion="Cuando confirmes una venta aparecerá aquí con su número y hora."
              />
            ) : (
              <ul className="divide-y divide-linea">
                {ventas.data?.items.map((venta) => (
                  <li key={venta.id} className="flex items-center justify-between gap-3 py-2">
                    <div>
                      <p className="text-sm font-semibold text-ink">Venta {venta.numero}</p>
                      <p className="text-xs text-muted">
                        {formatearFechaHora(venta.fecha)} · {venta.detalles.length} producto(s)
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold numero text-ink">
                        {formatearMoneda(venta.total)}
                      </p>
                      <Badge tono={venta.estado === 'ANULADO' ? 'peligro' : 'marca'}>
                        {etiquetaEstadoOperacion(venta.estado)}
                      </Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h3 className="etiqueta mb-2">Ingresos</h3>
            {ingresos.isLoading ? (
              <LoadingBlock etiqueta="Cargando ingresos…" />
            ) : ingresos.isError ? (
              <Notice tono="error" titulo="No se pudieron cargar los ingresos">
                {esSinPermisos(ingresos.error)
                  ? 'No tienes permiso para consultar el historial de abastecimientos.'
                  : mensajeDeError(ingresos.error)}
              </Notice>
            ) : (ingresos.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                titulo="Todavía no hay ingresos registrados"
                descripcion="Los abastecimientos confirmados se listarán aquí."
              />
            ) : (
              <ul className="divide-y divide-linea">
                {ingresos.data?.items.map((ingreso) => (
                  <li key={ingreso.id} className="flex items-center justify-between gap-3 py-2">
                    <div>
                      <p className="text-sm font-semibold text-ink">
                        Ingreso {ingreso.numero}
                      </p>
                      <p className="text-xs text-muted">
                        {ingreso.proveedor_nombre ?? 'Proveedor sin nombre'} ·{' '}
                        {formatearFechaHora(ingreso.fecha)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold numero text-ink">
                        {formatearMoneda(ingreso.total)}
                      </p>
                      <Badge tono={ingreso.estado === 'ANULADO' ? 'peligro' : 'marca'}>
                        {etiquetaEstadoOperacion(ingreso.estado)}
                      </Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </CardBody>
      </Card>

      <Card titulo="Otras áreas de trabajo">
        <CardBody className="flex flex-wrap gap-3">
          {puede('reportes.ver') ? (
            <Link
              to="/analizar"
              className="rounded-[6px] border border-linea px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
            >
              Analizar (reportes)
            </Link>
          ) : null}
          {puede('catalogo.ver') ? (
            <Link
              to="/gestionar/productos"
              className="rounded-[6px] border border-linea px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
            >
              Gestionar productos
            </Link>
          ) : null}
          {puede('proveedores.ver') ? (
            <Link
              to="/gestionar/proveedores"
              className="rounded-[6px] border border-linea px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
            >
              Gestionar proveedores
            </Link>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}
