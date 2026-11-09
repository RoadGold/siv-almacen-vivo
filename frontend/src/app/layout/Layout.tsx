import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { BarraPulso } from './BarraPulso';
import { MarcaSistema, NavegacionEstaciones, NavegacionSecundaria } from './Navegacion';
import { Button } from '@/design-system';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';

/**
 * Estructura general de la aplicación: barra de pulso, cabecera con las tres
 * estaciones, banda secundaria y el área de trabajo de la pantalla actual.
 */
export function Layout() {
  const { usuario, cerrar } = useAutenticacion();
  const navegar = useNavigate();

  function salir() {
    cerrar();
    navegar('/login', { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <a
        href="#contenido-principal"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-[6px] focus:bg-ink focus:px-3 focus:py-2 focus:text-sm focus:text-sobre-ink"
      >
        Saltar al contenido principal
      </a>

      <BarraPulso />

      <header className="border-b border-linea bg-surface">
        <div className="mx-auto flex max-w-contenido flex-wrap items-center justify-between gap-4 px-6 py-3">
          <MarcaSistema />
          <NavegacionEstaciones />
          <div className="flex items-center gap-3">
            {usuario ? (
              <div className="text-right leading-tight">
                <p className="text-sm font-semibold text-ink">{usuario.nombre}</p>
                <p className="text-2xs uppercase tracking-[0.1em] text-muted">
                  {usuario.roles.length > 0 ? usuario.roles.join(' · ') : 'sin rol asignado'}
                </p>
              </div>
            ) : null}
            <Button variante="secundario" tamano="sm" onClick={salir}>
              Cerrar sesión
            </Button>
          </div>
        </div>
        <div className="border-t border-linea bg-surface-tenue">
          <div className="mx-auto flex max-w-contenido flex-wrap items-center justify-between gap-3 px-6 py-1.5">
            <NavegacionSecundaria />
            <NavLink
              to="/"
              className={({ isActive }) =>
                [
                  'rounded-[6px] px-3 py-1.5 text-xs font-semibold transition-colors',
                  isActive ? 'bg-brand-tenue text-brand' : 'text-muted hover:text-brand',
                ].join(' ')
              }
            >
              Inicio
            </NavLink>
          </div>
        </div>
      </header>

      <main id="contenido-principal" className="mx-auto w-full max-w-contenido flex-1 px-6 py-6">
        <Outlet />
      </main>

      <footer className="border-t border-linea bg-surface">
        <div className="mx-auto max-w-contenido px-6 py-3 text-2xs uppercase tracking-[0.12em] text-muted">
          SIV · Almacén Vivo · Sistema local de inventario
        </div>
      </footer>
    </div>
  );
}
