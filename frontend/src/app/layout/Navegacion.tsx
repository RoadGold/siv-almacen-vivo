import { NavLink } from 'react-router-dom';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';

interface Estacion {
  ruta: string;
  titulo: string;
  descripcion: string;
  permiso?: string;
}

const ESTACIONES: Estacion[] = [
  {
    ruta: '/vender',
    titulo: 'Vender',
    descripcion: 'Nueva venta',
    permiso: 'ventas.crear',
  },
  {
    ruta: '/recibir',
    titulo: 'Recibir',
    descripcion: 'Nuevo ingreso',
    permiso: 'abastecimientos.crear',
  },
  {
    ruta: '/explorar',
    titulo: 'Explorar',
    descripcion: 'Buscar stock',
    permiso: 'inventario.ver',
  },
];

const SECUNDARIOS: { ruta: string; titulo: string; permiso?: string }[] = [
  { ruta: '/analizar', titulo: 'Analizar', permiso: 'reportes.ver' },
  { ruta: '/gestionar/productos', titulo: 'Gestionar productos', permiso: 'catalogo.ver' },
  { ruta: '/gestionar/proveedores', titulo: 'Gestionar proveedores', permiso: 'proveedores.ver' },
  { ruta: '/administrar', titulo: 'Administrar', permiso: 'admin.usuarios' },
];

/** Navegación principal: tres estaciones de trabajo. */
export function NavegacionEstaciones() {
  const { puede } = useAutenticacion();
  const visibles = ESTACIONES.filter((estacion) => !estacion.permiso || puede(estacion.permiso));

  return (
    <nav aria-label="Estaciones de trabajo" className="flex flex-wrap items-center gap-2">
      {visibles.map((estacion) => (
        <NavLink
          key={estacion.ruta}
          to={estacion.ruta}
          className={({ isActive }) =>
            [
              'group rounded-[6px] border px-4 py-2 transition-colors',
              isActive
                ? 'border-brand bg-brand text-white'
                : 'border-linea bg-surface text-ink hover:border-brand hover:text-brand',
            ].join(' ')
          }
        >
          {({ isActive }) => (
            <span className="flex flex-col leading-tight">
              <span className="text-sm font-bold uppercase tracking-[0.1em]">{estacion.titulo}</span>
              <span
                className={[
                  'text-2xs',
                  isActive ? 'text-white/85' : 'text-muted group-hover:text-brand',
                ].join(' ')}
              >
                {estacion.descripcion}
              </span>
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

/** Banda secundaria: herramientas menos frecuentes. */
export function NavegacionSecundaria() {
  const { puede } = useAutenticacion();
  const visibles = SECUNDARIOS.filter((item) => !item.permiso || puede(item.permiso));

  if (visibles.length === 0) return null;

  return (
    <nav aria-label="Herramientas secundarias" className="flex flex-wrap items-center gap-1">
      {visibles.map((item) => (
        <NavLink
          key={item.ruta}
          to={item.ruta}
          className={({ isActive }) =>
            [
              'rounded-[6px] px-3 py-1.5 text-xs font-semibold transition-colors',
              isActive ? 'bg-brand-tenue text-brand' : 'text-muted hover:text-brand',
            ].join(' ')
          }
        >
          {item.titulo}
        </NavLink>
      ))}
    </nav>
  );
}

/** Identidad del sistema con acceso al inicio. */
export function MarcaSistema() {
  return (
    <NavLink to="/" className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className="flex h-9 w-9 items-center justify-center rounded-[6px] bg-brand text-sm font-bold text-white"
      >
        SV
      </span>
      <span className="flex flex-col leading-tight">
        <span className="text-sm font-bold uppercase tracking-[0.16em] text-ink">
          SIV · Almacén Vivo
        </span>
        <span className="text-2xs uppercase tracking-[0.12em] text-muted">
          Inventario · Proveedores · Ventas
        </span>
      </span>
    </NavLink>
  );
}
