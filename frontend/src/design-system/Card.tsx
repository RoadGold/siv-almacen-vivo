import type { ReactNode } from 'react';

export interface CardProps {
  children: ReactNode;
  className?: string;
  /** Título de la sección; se usa como encabezado semántico. */
  titulo?: string;
  /** Texto auxiliar bajo el título. */
  subtitulo?: string;
  acciones?: ReactNode;
  /** Nivel del encabezado (2 por defecto). */
  nivel?: 2 | 3;
}

/** Panel blanco con borde fino: unidad visual por defecto del sistema. */
export function Card({
  children,
  className = '',
  titulo,
  subtitulo,
  acciones,
  nivel = 2,
}: CardProps) {
  const Titulo = nivel === 2 ? 'h2' : 'h3';
  return (
    <section
      className={['rounded-tarjeta border border-linea bg-surface shadow-panel', className]
        .filter(Boolean)
        .join(' ')}
    >
      {titulo ? (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-linea px-4 py-3">
          <div>
            <Titulo className="text-base font-semibold text-ink">{titulo}</Titulo>
            {subtitulo ? <p className="mt-0.5 text-xs text-muted">{subtitulo}</p> : null}
          </div>
          {acciones ? <div className="flex flex-wrap items-center gap-2">{acciones}</div> : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}

/** Bloque con padding estándar para el contenido de un panel. */
export function CardBody({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={['px-4 py-4', className].filter(Boolean).join(' ')}>{children}</div>;
}
