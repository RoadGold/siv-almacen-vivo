import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import { Spinner } from '@/design-system';

/**
 * Guarda de rutas: exige sesión iniciada y devuelve al acceso cuando falta el token.
 */
export function RutaPrivada({ children }: { children: ReactNode }) {
  const { usuario, verificando } = useAutenticacion();
  const ubicacion = useLocation();

  if (verificando) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <Spinner etiqueta="Verificando la sesión…" />
      </div>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" replace state={{ desde: ubicacion.pathname }} />;
  }

  return <>{children}</>;
}
