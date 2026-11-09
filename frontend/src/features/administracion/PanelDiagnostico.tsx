import { useQuery } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  CardBody,
  Notice,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import { sistemaApi } from '@/shared/api/endpoints';
import { URL_API } from '@/shared/api/client';
import { formatearFechaHora } from '@/shared/format/formato';
import { mensajeDeError } from '@/shared/hooks/errores';

/** Panel de diagnóstico del servidor local (plan §4.1, paso 10). */
export function PanelDiagnostico() {
  const salud = useQuery({
    queryKey: claves.salud,
    queryFn: () => sistemaApi.salud(),
    staleTime: 10_000,
  });

  const datos = salud.data;

  return (
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
          <DatoDiagnostico etiqueta="Última consulta" valor={formatearFechaHora(new Date().toISOString())} />
        </dl>

        <p className="text-xs text-muted">
          URL base de la API: <span className="numero">{URL_API}</span>. El sistema opera sin
          conexión a internet: solo necesita que este servidor local esté encendido.
        </p>
      </CardBody>
    </Card>
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
