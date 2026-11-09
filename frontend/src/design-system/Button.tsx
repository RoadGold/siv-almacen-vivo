import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type VarianteBoton = 'primario' | 'acento' | 'secundario' | 'fantasma' | 'peligro';
export type TamanoBoton = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: VarianteBoton;
  tamano?: TamanoBoton;
  /** Muestra un indicador y desactiva el botón (operación en curso). */
  cargando?: boolean;
  /** Texto visible mientras `cargando` es verdadero. */
  textoCargando?: string;
  anchoCompleto?: boolean;
  icono?: ReactNode;
}

const VARIANTES: Record<VarianteBoton, string> = {
  primario:
    'bg-brand text-white border border-brand hover:bg-brand-hondo hover:border-brand-hondo',
  acento:
    'bg-accent text-ink border border-accent hover:bg-[#d6ea82] hover:border-[#d6ea82]',
  secundario:
    'bg-surface text-ink border border-linea-fuerte hover:border-brand hover:text-brand',
  fantasma:
    'bg-transparent text-brand border border-transparent hover:bg-brand-tenue',
  peligro: 'bg-danger text-white border border-danger hover:bg-[#9c332c] hover:border-[#9c332c]',
};

const TAMANOS: Record<TamanoBoton, string> = {
  sm: 'text-xs px-3 py-1.5 gap-1.5',
  md: 'text-sm px-4 py-2 gap-2',
  lg: 'text-base px-5 py-3 gap-2',
};

/** Botón base del sistema visual. */
export function Button({
  variante = 'secundario',
  tamano = 'md',
  cargando = false,
  textoCargando,
  anchoCompleto = false,
  icono,
  children,
  className = '',
  disabled,
  type = 'button',
  ...resto
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      className={[
        'inline-flex items-center justify-center rounded-[6px] font-semibold transition-colors',
        'disabled:cursor-not-allowed disabled:opacity-55',
        VARIANTES[variante],
        TAMANOS[tamano],
        anchoCompleto ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...resto}
    >
      {cargando ? (
        <span
          aria-hidden="true"
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      ) : (
        icono
      )}
      <span>{cargando && textoCargando ? textoCargando : children}</span>
    </button>
  );
}
