/**
 * Estado de la impresora de tickets y ticket de prueba.
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { Badge, Button, Card, CardBody, LoadingBlock, Notice, useToast } from '@/design-system';
import { impresoraApi } from '@/shared/api/endpoints';
import { mensajeDeError } from '@/shared/hooks/errores';

export function PanelImpresora() {
  const { notificar } = useToast();

  const consulta = useQuery({
    queryKey: ['impresora', 'estado'],
    queryFn: () => impresoraApi.estado(),
    refetchInterval: 30_000,
  });

  const prueba = useMutation({
    mutationFn: () => impresoraApi.prueba(),
    onSuccess: (resultado) => notificar(resultado.mensaje, 'exito'),
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  if (consulta.isLoading) {
    return <LoadingBlock etiqueta="Consultando la impresora…" />;
  }

  if (consulta.isError) {
    return (
      <div className="p-4">
        <Notice tono="error" titulo="No se pudo consultar la impresora">
          {mensajeDeError(consulta.error)}
        </Notice>
      </div>
    );
  }

  const estado = consulta.data;
  if (!estado) {
    return (
      <div className="p-4">
        <Notice tono="aviso" titulo="Sin datos de la impresora">
          No se pudo obtener el estado de la impresora.
        </Notice>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card titulo="Impresora de tickets" subtitulo="Impresión ESC/POS por red">
        <CardBody className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <Badge tono={estado.activa ? 'marca' : 'neutro'}>
              {estado.activa ? 'Activada' : 'Desactivada'}
            </Badge>
            <Badge tono={estado.conectada ? 'marca' : 'peligro'}>
              {estado.conectada ? 'Conectada' : 'Sin conexión'}
            </Badge>
            <span className="text-sm text-muted">
              {estado.host}:{estado.puerto} · {estado.columnas} columnas ·{' '}
              {estado.cortar ? 'con corte' : 'sin corte'} ·{' '}
              {estado.qr ? 'con QR' : 'sin QR'}
            </span>
          </div>

          <p className="text-sm text-ink">{estado.mensaje}</p>

          <div className="flex flex-wrap gap-2">
            <Button
              variante="primario"
              disabled={!estado.activa || prueba.isPending}
              cargando={prueba.isPending}
              textoCargando="Imprimiendo…"
              onClick={() => prueba.mutate()}
            >
              Imprimir ticket de prueba
            </Button>
            <Button variante="secundario" onClick={() => consulta.refetch()}>
              Consultar de nuevo
            </Button>
          </div>

          <Notice tono="info" titulo="Para activarla">
            Edite <code>IMPRESORA_ACTIVA</code>, <code>IMPRESORA_HOST</code> y{' '}
            <code>IMPRESORA_PUERTO</code> en el archivo <code>.env</code> y reinicie el
            servidor. La dirección IP y el puerto se comprueban con el script de prueba física.
          </Notice>
        </CardBody>
      </Card>
    </div>
  );
}
