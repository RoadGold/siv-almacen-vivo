/**
 * Estado de la impresora de tickets.
 *
 * Se separa en dos bloques:
 *  · **Estado en vivo**: si el puerto de impresión responde (comprobación que
 *    no imprime nada: solo abre y cierra la conexión).
 *  · **Especificaciones declaradas**: modelo, ancho y resolución. La impresora
 *    ESC/POS por red no informa de su modelo, así que se anotan en la
 *    configuración del negocio.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Badge, Button, Card, CardBody, LoadingBlock, Notice, useToast } from '@/design-system';
import { impresoraApi } from '@/shared/api/endpoints';
import { mensajeDeError } from '@/shared/hooks/errores';

export function PanelImpresora() {
  const { notificar } = useToast();
  const [consultarEquipo, setConsultarEquipo] = useState(false);

  const consulta = useQuery({
    queryKey: ['impresora', 'estado', consultarEquipo],
    queryFn: () => impresoraApi.estado(consultarEquipo),
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

  const estadoEquipo = estado.estado_equipo;

  return (
    <div className="flex flex-col gap-4">
      <Card
        titulo="Estado en vivo"
        subtitulo="Comprobación que no imprime nada: solo abre y cierra la conexión"
      >
        <CardBody className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <Badge tono={estado.activa ? 'marca' : 'neutro'}>
              {estado.activa ? 'Activada' : 'Desactivada'}
            </Badge>
            <Badge tono={estado.conectada ? 'marca' : 'peligro'}>
              {estado.conectada ? 'Conectada' : 'Sin conexión'}
            </Badge>
            <span className="text-sm text-muted">
              {estado.host}:{estado.puerto}
              {estado.tiempo_ms !== null && estado.tiempo_ms !== undefined
                ? ` · respondió en ${estado.tiempo_ms} ms`
                : ''}
            </span>
          </div>

          <p className="text-sm text-ink">{estado.mensaje}</p>

          {!estado.conectada && estado.motivo && estado.motivo !== 'desactivada' ? (
            <Notice tono="aviso" titulo="Qué revisar">
              {estado.motivo === 'timeout'
                ? 'La impresora no contestó a tiempo: compruebe que esté encendida y que la computadora llegue a su red (ipconfig).'
                : estado.motivo === 'rechazada'
                  ? 'El puerto rechazó la conexión: algunas clones imprimen en el 9200 en vez del 9100. Pruebe con otro puerto.'
                  : 'No hay ruta hacia la impresora: revise la red y el firewall.'}
            </Notice>
          ) : null}

          {estadoEquipo ? (
            <Notice
              tono={estadoEquipo.respondio ? 'info' : 'aviso'}
              titulo="Estado en vivo del equipo"
            >
              {estadoEquipo.mensaje}
              {estadoEquipo.respondio && estadoEquipo.avisos?.length ? (
                <span className="mt-1 block text-xs">
                  Según el estándar ESC/POS; algunas clones usan otro criterio.
                </span>
              ) : null}
            </Notice>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              variante="secundario"
              onClick={() => void consulta.refetch()}
              cargando={consulta.isFetching}
              textoCargando="Comprobando…"
            >
              Comprobar conexión (sin imprimir)
            </Button>
            <label className="flex items-center gap-2 text-xs text-muted">
              <input
                type="checkbox"
                checked={consultarEquipo}
                onChange={(evento) => setConsultarEquipo(evento.target.checked)}
              />
              Consultar el estado en vivo del equipo (no imprime, pero algunos
              equipos no lo soportan)
            </label>
          </div>
        </CardBody>
      </Card>

      <Card
        titulo="Especificaciones declaradas"
        subtitulo="La impresora ESC/POS por red no informa de su modelo: se anotan aquí"
      >
        <CardBody className="flex flex-col gap-3">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="etiqueta">Modelo</dt>
              <dd className="text-sm text-ink">{estado.modelo || 'Sin anotar'}</dd>
            </div>
            <div>
              <dt className="etiqueta">Ancho del papel</dt>
              <dd className="text-sm text-ink">
                {estado.ancho_mm || '80'} mm · {estado.columnas} columnas
              </dd>
            </div>
            <div>
              <dt className="etiqueta">Resolución</dt>
              <dd className="text-sm text-ink">{estado.resolucion || '203'} dpi</dd>
            </div>
            <div>
              <dt className="etiqueta">Dirección de impresión</dt>
              <dd className="text-sm text-ink">
                {estado.host}:{estado.puerto}
              </dd>
            </div>
            <div>
              <dt className="etiqueta">Corte de papel</dt>
              <dd className="text-sm text-ink">{estado.cortar ? 'Automático' : 'Manual'}</dd>
            </div>
            <div>
              <dt className="etiqueta">Código QR</dt>
              <dd className="text-sm text-ink">{estado.qr ? 'Incluido' : 'No incluido'}</dd>
            </div>
          </dl>

          <Notice tono="info" titulo="Dónde se anota">
            El modelo, el ancho y la resolución se editan en{' '}
            <strong>Administrar → Configuración</strong>. La dirección IP y el
            puerto, en el archivo <code>.env</code> (<code>IMPRESORA_HOST</code>,{' '}
            <code>IMPRESORA_PUERTO</code>) y reiniciando el servidor.
          </Notice>

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
            <span className="self-center text-xs text-muted">
              Esta es la única acción que gasta papel.
            </span>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
