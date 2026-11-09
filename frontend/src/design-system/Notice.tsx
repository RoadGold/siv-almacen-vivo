import type { ReactNode } from 'react';

export type TonoAviso = 'info' | 'exito' | 'aviso' | 'error';

export interface NoticeProps {
  children: ReactNode;
  tono?: TonoAviso;
  titulo?: string;
  className?: string;
  acciones?: ReactNode;
}

/**
 * Aviso en línea. Siempre incluye una palabra que identifica el estado,
 * de modo que el color no sea la única señal.
 */
export function Notice({ children, tono = 'info', titulo, className = '', acciones }: NoticeProps) {
  const estilos: Record<TonoAviso, { contenedor: string; texto: string; etiqueta: string }> = {
    info: {
      contenedor: 'border-linea-fuerte bg-surface-tenue',
      texto: 'text-ink',
      etiqueta: 'Aviso',
    },
    exito: {
      contenedor: 'border-brand bg-brand-tenue',
      texto: 'text-ink',
      etiqueta: 'Listo',
    },
    aviso: {
      contenedor: 'border-warning bg-warning-tenue',
      texto: 'text-ink',
      etiqueta: 'Atención',
    },
    error: {
      contenedor: 'border-danger bg-danger-tenue',
      texto: 'text-ink',
      etiqueta: 'Problema',
    },
  };

  const estilo = estilos[tono];

  return (
    <div
      role={tono === 'error' ? 'alert' : 'status'}
      className={[
        'flex flex-col gap-2 rounded-[6px] border px-4 py-3 text-sm',
        estilo.contenedor,
        estilo.texto,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex flex-wrap items-start gap-2">
        <span className="etiqueta mt-0.5">{estilo.etiqueta}</span>
        {titulo ? <p className="font-semibold">{titulo}</p> : null}
      </div>
      <div className="leading-relaxed">{children}</div>
      {acciones ? <div className="flex flex-wrap gap-2 pt-1">{acciones}</div> : null}
    </div>
  );
}
