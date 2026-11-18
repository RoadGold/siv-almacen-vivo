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

/**
 * Nombre visible del dato y ejemplo de lo que se debe escribir en cada ajuste.
 * Las claves son las que usa el backend en `configuracion`.
 *
 * `ejemplo` es el placeholder del cuadro de texto; `pista` es el ejemplo que se
 * muestra en las listas desplegables (un `Select` no admite placeholder).
 */
const CAMPOS: Record<string, { etiqueta: string; ejemplo?: string; pista?: string }> = {
  negocio_nombre: { etiqueta: 'Nombre del negocio', ejemplo: 'Almacén Vivo S.A.C.' },
  negocio_ruc: { etiqueta: 'RUC', ejemplo: '20512345678' },
  negocio_direccion: { etiqueta: 'Dirección', ejemplo: 'Av. Los Frutales 1200, Lima' },
  negocio_telefono: { etiqueta: 'Teléfono', ejemplo: '01 555 0123' },
  ticket_pie: { etiqueta: 'Mensaje del pie', ejemplo: '¡Gracias por su compra!' },
  ticket_ancho: {
    etiqueta: 'Ancho del ticket',
    pista: 'Ejemplo: 80 mm para un ticket de 48 columnas.',
  },
  ticket_mostrar_precio_original: {
    etiqueta: 'Mostrar precio original',
    pista: 'Ejemplo: Sí, para tachar el precio original junto al precio final.',
  },
  ticket_mostrar_qr: {
    etiqueta: 'Mostrar QR',
    pista: 'Ejemplo: Sí, para imprimir el código QR de la venta.',
  },
  venta_descuento_maximo_porcentaje: {
    etiqueta: 'Límite de descuento (%)',
    ejemplo: '20',
  },
  venta_descuento_maximo_monto: {
    etiqueta: 'Límite de descuento (S/)',
    ejemplo: '50',
  },
};

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
    const definicion = CAMPOS[clave] ?? { etiqueta: clave.replace(/_/g, ' ') };
    const id = `config-${clave}`;
    // La descripción del backend y la pista de ejemplo se muestran juntas.
    const ayuda = [descripciones[clave], definicion.pista].filter(Boolean).join(' ');

    // Cada control va dentro de su propio `Field` para que el ejemplo se
    // aplique como placeholder del cuadro de texto.
    if (clave === 'ticket_mostrar_precio_original' || clave === 'ticket_mostrar_qr') {
      return (
        <Field key={clave} htmlFor={id} etiqueta={definicion.etiqueta} ayuda={ayuda}>
          <Select
            id={id}
            value={valores[clave] ?? ''}
            onChange={(evento) =>
              setValores((actuales) => ({ ...actuales, [clave]: evento.target.value }))
            }
          >
            <option value="si">Sí</option>
            <option value="no">No</option>
          </Select>
        </Field>
      );
    }

    if (clave === 'ticket_ancho') {
      return (
        <Field key={clave} htmlFor={id} etiqueta={definicion.etiqueta} ayuda={ayuda}>
          <Select
            id={id}
            value={valores[clave] ?? '80'}
            onChange={(evento) =>
              setValores((actuales) => ({ ...actuales, [clave]: evento.target.value }))
            }
          >
            <option value="80">80 mm (48 columnas)</option>
            <option value="58">58 mm (32 columnas)</option>
          </Select>
        </Field>
      );
    }

    return (
      <Field
        key={clave}
        htmlFor={id}
        etiqueta={definicion.etiqueta}
        ejemplo={definicion.ejemplo}
        ayuda={ayuda}
      >
        <Input
          id={id}
          value={valores[clave] ?? ''}
          onChange={(evento) =>
            setValores((actuales) => ({ ...actuales, [clave]: evento.target.value }))
          }
        />
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
