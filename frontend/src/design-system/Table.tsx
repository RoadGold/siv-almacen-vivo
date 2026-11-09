import type { ReactNode } from 'react';

export interface TableProps {
  children: ReactNode;
  /** Texto alternativo para lectores de pantalla cuando no hay encabezado. */
  descripcion?: string;
  className?: string;
}

/** Envoltorio de tabla con desplazamiento horizontal controlado. */
export function Table({ children, descripcion, className = '' }: TableProps) {
  return (
    <div className={`w-full overflow-x-auto ${className}`}>
      <table className="w-full border-collapse text-sm" aria-label={descripcion}>
        {children}
      </table>
    </div>
  );
}

export function TableHead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-linea bg-[#faf9f5]">
      <tr>{children}</tr>
    </thead>
  );
}

export function TableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-linea">{children}</tbody>;
}

export function TableRow({
  children,
  onClick,
  activa = false,
}: {
  children: ReactNode;
  onClick?: () => void;
  activa?: boolean;
}) {
  return (
    <tr
      onClick={onClick}
      className={[
        'align-middle',
        onClick ? 'cursor-pointer hover:bg-[#faf9f5]' : '',
        activa ? 'bg-brand-tenue' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </tr>
  );
}

export function TableHeader({
  children,
  className = '',
  scope = 'col',
}: {
  children: ReactNode;
  className?: string;
  scope?: 'col' | 'row';
}) {
  return (
    <th
      scope={scope}
      className={[
        'px-3 py-2 text-left text-2xs font-semibold uppercase tracking-[0.1em] text-muted',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </th>
  );
}

export function TableCell({
  children,
  className = '',
  numerica = false,
}: {
  children: ReactNode;
  className?: string;
  numerica?: boolean;
}) {
  return (
    <td
      className={[
        'px-3 py-2 text-sm text-ink',
        numerica ? 'text-right numero' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </td>
  );
}

/** Pie de tabla para paginación y resúmenes. */
export function TableFooter({ children }: { children: ReactNode }) {
  return (
    <tfoot className="border-t border-linea bg-[#faf9f5] text-sm">
      <tr>{children}</tr>
    </tfoot>
  );
}
