import { useQuery } from '@tanstack/react-query';
import { claves } from '@/shared/api/clavesConsulta';
import { sistemaApi } from '@/shared/api/endpoints';
import { formatearHora } from '@/shared/format/formato';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import { suscribirOperacion, type Operacion } from '@/shared/estado/operaciones';
import { useEffect, useState } from 'react';

/**
 * Barra de pulso: franja superior con el estado del servidor local,
 * el usuario activo y la última operación realizada.
 */
export function BarraPulso() {
  const { usuario } = useAutenticacion();
  const [operacion, setOperacion] = useState<Operacion | null>(null);

  useEffect(() => suscribirOperacion(setOperacion), []);

  const { data, isError, isLoading } = useQuery({
    queryKey: claves.salud,
    queryFn: () => sistemaApi.salud(),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  const conectado = !isError && !isLoading;

  return (
    <div className="border-b border-linea bg-[#f1efe8] text-2xs text-ink-suave">
      <div className="mx-auto flex max-w-contenido flex-wrap items-center justify-between gap-x-6 gap-y-1 px-6 py-1.5">
        <p className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className={[
              'inline-block h-2 w-2 rounded-full',
              conectado ? 'bg-brand' : 'bg-danger',
            ].join(' ')}
          />
          <span className="font-semibold uppercase tracking-[0.12em]">
            {isLoading
              ? 'Comprobando servidor'
              : conectado
                ? 'Servidor local conectado'
                : 'Servidor local sin conexión'}
          </span>
          {data?.servicio ? <span className="hidden sm:inline">· {data.servicio}</span> : null}
        </p>

        <p className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>
            <span className="font-semibold uppercase tracking-[0.12em]">Última operación: </span>
            {operacion
              ? `${operacion.descripcion} · ${formatearHora(operacion.momento)}`
              : 'todavía no hay operaciones'}
          </span>
          <span className="hidden sm:inline">
            <span className="font-semibold uppercase tracking-[0.12em]">Usuario: </span>
            {usuario ? `${usuario.nombre} (${usuario.usuario})` : '—'}
          </span>
        </p>
      </div>
    </div>
  );
}
