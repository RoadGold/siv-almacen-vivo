import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { ToastProvider } from '@/design-system';
import { ProveedorAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import { ProveedorTema } from '@/shared/tema/ProveedorTema';
import { ErrorApi } from '@/shared/api/client';

/** Proveedores globales de la aplicación. */
export function ProveedoresApp({ children }: { children: ReactNode }) {
  const [cliente] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 5 * 60_000,
            refetchOnWindowFocus: false,
            retry: (intento, error) => {
              // No se reintenta ante errores de negocio o de autorización.
              if (error instanceof ErrorApi && error.estado >= 400 && error.estado < 500) return false;
              return intento < 1;
            },
          },
          mutations: { retry: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={cliente}>
      <ProveedorTema>
        <ProveedorAutenticacion>
          <ToastProvider>{children}</ToastProvider>
        </ProveedorAutenticacion>
      </ProveedorTema>
    </QueryClientProvider>
  );
}
