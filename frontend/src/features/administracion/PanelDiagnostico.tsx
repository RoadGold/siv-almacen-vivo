import { useQuery } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  CardBody,
  Notice,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import { adminApi, sistemaApi } from '@/shared/api/endpoints';
import { URL_API } from '@/shared/api/client';
import { formatearFechaHora } from '@/shared/format/formato';
import { mensajeDeError } from '@/shared/hooks/errores';

/** Tablas que se revisan para saber si la base tiene operación pendiente. */
const TABLAS_OPERACION = [
  'ventas',
  'abastecimientos',
  'ajustes_inventario',
  'impresiones_venta',
  'auditoria',
] as const;

/** Tablas del catálogo y del inventario. */
const TABLAS_ESTRUCTURA = [
  'productos',
  'presentaciones_producto',
  'proveedores',
  'marcas',
  'categorias',
  'lotes_inventario',
  'existencias',
] as const;

/** Panel de diagnóstico del servidor local (plan §4.1, paso 10). */
export function PanelDiagnostico() {
  const salud = useQuery({
    queryKey: claves.salud,
    queryFn: () => sistemaApi.salud(),
    staleTime: 10_000,
  });

  const base = useQuery({
    queryKey: ['admin', 'estado-base'],
    queryFn: () => adminApi.estadoBase(),
    retry: false,
  });

  const datos = salud.data;

  return (
    <div className="flex flex-col gap-4">
      <Card
        titulo="Diagnóstico del servidor local"
        subtitulo="Estado del backend al que esta interfaz está conectada"
        acciones={
          <Button
            variante="secundario"
            tamano="sm"
            cargando={salud.isFetching}
            textoCargando="Consultando…"
            onClick={() => void salud.refetch()}
          >
            Consultar ahora
          </Button>
        }
      >
        <CardBody className="flex flex-col gap-4">
          {salud.isError ? (
            <Notice tono="error" titulo="El servidor local no responde">
              {mensajeDeError(salud.error)}
            </Notice>
          ) : null}

          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <DatoDiagnostico
              etiqueta="Estado"
              valor={
                salud.isLoading
                  ? 'Comprobando…'
                  : datos
                    ? datos.estado === 'ok'
                      ? 'Operativo'
                      : datos.estado
                    : '—'
              }
              tono={datos?.estado === 'ok' ? 'marca' : 'peligro'}
            />
            <DatoDiagnostico etiqueta="Servicio" valor={datos?.servicio ?? '—'} />
            <DatoDiagnostico etiqueta="Versión" valor={datos?.version ?? '—'} />
            <DatoDiagnostico etiqueta="Entorno" valor={datos?.entorno ?? '—'} />
            <DatoDiagnostico etiqueta="Moneda" valor={datos?.moneda ?? '—'} />
            <DatoDiagnostico
              etiqueta="Última consulta"
              valor={
                salud.dataUpdatedAt ? formatearFechaHora(new Date(salud.dataUpdatedAt).toISOString()) : '—'
              }
            />
          </dl>

          <p className="text-xs text-muted">
            URL base de la API: <span className="numero">{URL_API}</span>. El sistema opera sin
            conexión a internet: solo necesita que este servidor local esté encendido.
          </p>
        </CardBody>
      </Card>

      <Card
        titulo="Estado de la base de datos"
        subtitulo="Qué contiene la base y si está limpia (sin operación pendiente)"
      >
        <CardBody className="flex flex-col gap-4">
          {base.isError ? (
            <Notice tono="aviso" titulo="No se pudo consultar el estado de la base">
              {mensajeDeError(base.error)}
            </Notice>
          ) : base.isLoading ? (
            <p className="text-sm text-muted">Consultando la base de datos…</p>
          ) : base.data ? (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <Badge tono={base.data.operacion_pendiente ? 'aviso' : 'marca'}>
                  {base.data.operacion_pendiente
                    ? 'Con operación pendiente'
                    : 'Sin operación pendiente'}
                </Badge>
                <Badge tono={base.data.diferencias_conciliacion === 0 ? 'marca' : 'peligro'}>
                  {base.data.diferencias_conciliacion === 0
                    ? 'Existencias cuadradas con los lotes'
                    : `${base.data.diferencias_conciliacion} diferencia(s)`}
                </Badge>
                <span className="text-sm text-muted">
                  Esquema: {base.data.version_esquema ?? 'desconocido'}
                </span>
              </div>

              <div>
                <p className="etiqueta mb-1">Operación</p>
                <ul className="flex flex-wrap gap-2">
                  {TABLAS_OPERACION.map((tabla) => (
                    <li
                      key={tabla}
                      className="rounded-[6px] border border-linea px-2 py-1 text-xs text-muted"
                    >
                      {tabla}:{' '}
                      <span className="numero font-semibold text-ink">
                        {base.data.conteos[tabla] ?? 0}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <p className="etiqueta mb-1">Catálogo e inventario</p>
                <ul className="flex flex-wrap gap-2">
                  {TABLAS_ESTRUCTURA.map((tabla) => (
                    <li
                      key={tabla}
                      className="rounded-[6px] border border-linea px-2 py-1 text-xs text-muted"
                    >
                      {tabla}:{' '}
                      <span className="numero font-semibold text-ink">
                        {base.data.conteos[tabla] ?? 0}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {base.data.diferencias_conciliacion > 0 ? (
                <Notice tono="error" titulo="Las existencias no cuadran con los lotes">
                  Revise el detalle con el reporte de conciliación de inventario.
                </Notice>
              ) : null}
            </>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}

/** Dato del diagnóstico con etiqueta y valor. */
function DatoDiagnostico({
  etiqueta,
  valor,
  tono,
}: {
  etiqueta: string;
  valor: string;
  tono?: 'marca' | 'peligro';
}) {
  return (
    <div className="rounded-[6px] border border-linea px-4 py-3">
      <dt className="etiqueta">{etiqueta}</dt>
      <dd className="mt-1 flex items-center gap-2 text-sm font-semibold text-ink">
        {tono ? <Badge tono={tono}>{valor}</Badge> : valor}
      </dd>
    </div>
  );
}
