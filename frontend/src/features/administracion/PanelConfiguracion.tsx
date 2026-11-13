/**
 * Configuración del negocio y de la caja.
 *
 * Datos que aparecen en el ticket (nombre, RUC, dirección, teléfono, mensaje
 * final) y reglas de la caja (límite de descuento, formato del ticket).
 */

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  CardBody,
  Field,
  Input,
  LoadingBlock,
  Notice,
  Select,
  useToast,
} from '@/design-system';
import { configuracionApi } from '@/shared/api/endpoints';
import { mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';

export function PanelConfiguracion() {
  const [valores, setValores] = useState<Record<string, string>>({});
  const cliente = useQueryClient();
  const { notificar } = useToast();

  const consulta = useQuery({
    queryKey: ['configuracion'],
    queryFn: () => configuracionApi.leer(),
  });

  useEffect(() => {
    if (consulta.data) setValores(consulta.data.valores);
  }, [consulta.data]);

  const guardar = useMutation({
    mutationFn: (cambios: Record<string, string>) =>
      configuracionApi.guardar(cambios),
    onSuccess: (respuesta) => {
      setValores(respuesta.valores);
      notificar('Configuración guardada.', 'exito');
      registrarOperacion('Configuración del negocio');
      cliente.invalidateQueries({ queryKey: ['configuracion'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  if (consulta.isLoading) {
    return <LoadingBlock etiqueta="Cargando configuración…" />;
  }

  if (consulta.isError) {
    return (
      <div className="p-4">
        <Notice tono="error" titulo="No se pudo cargar la configuración">
          {mensajeDeError(consulta.error)}
        </Notice>
      </div>
    );
  }

  const descripciones = consulta.data?.descripciones ?? {};

  function campo(clave: string) {
    return (
      <Field
        key={clave}
        htmlFor={`config-${clave}`}
        etiqueta={clave.replace(/_/g, ' ')}
        ayuda={descripciones[clave]}
      >
        {clave === 'ticket_mostrar_precio_original' || clave === 'ticket_mostrar_qr' ? (
          <Select
            id={`config-${clave}`}
            value={valores[clave] ?? ''}
            onChange={(evento) =>
              setValores((actuales) => ({ ...actuales, [clave]: evento.target.value }))
            }
          >
            <option value="si">Sí</option>
            <option value="no">No</option>
          </Select>
        ) : clave === 'ticket_ancho' ? (
          <Select
            id={`config-${clave}`}
            value={valores[clave] ?? '80'}
            onChange={(evento) =>
              setValores((actuales) => ({ ...actuales, [clave]: evento.target.value }))
            }
          >
            <option value="80">80 mm (48 columnas)</option>
            <option value="58">58 mm (32 columnas)</option>
          </Select>
        ) : (
          <Input
            id={`config-${clave}`}
            value={valores[clave] ?? ''}
            onChange={(evento) =>
              setValores((actuales) => ({ ...actuales, [clave]: evento.target.value }))
            }
          />
        )}
      </Field>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card titulo="Datos del negocio" subtitulo="Aparecen en el encabezado del ticket">
        <CardBody className="grid gap-3 md:grid-cols-2">
          {campo('negocio_nombre')}
          {campo('negocio_ruc')}
          {campo('negocio_direccion')}
          {campo('negocio_telefono')}
          {campo('ticket_pie')}
        </CardBody>
      </Card>

      <Card titulo="Formato del ticket">
        <CardBody className="grid gap-3 md:grid-cols-3">
          {campo('ticket_ancho')}
          {campo('ticket_mostrar_precio_original')}
          {campo('ticket_mostrar_qr')}
        </CardBody>
      </Card>

      <Card
        titulo="Reglas de la caja"
        subtitulo="Controlan hasta dónde puede llegar el descuento del vendedor"
      >
        <CardBody className="grid gap-3 md:grid-cols-2">
          {campo('venta_descuento_maximo_porcentaje')}
          {campo('venta_descuento_maximo_monto')}
        </CardBody>
      </Card>

      <div className="flex justify-end">
        <Button
          variante="primario"
          cargando={guardar.isPending}
          textoCargando="Guardando…"
          onClick={() => guardar.mutate(valores)}
        >
          Guardar configuración
        </Button>
      </div>
    </div>
  );
}
