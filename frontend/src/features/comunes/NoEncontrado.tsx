import { Link } from 'react-router-dom';
import { Card, CardBody, EmptyState } from '@/design-system';

/** Pantalla de ruta inexistente. */
export function NoEncontrado() {
  return (
    <div className="flex flex-col gap-4">
      <Card titulo="Página no encontrada">
        <CardBody>
          <EmptyState
            titulo="Esta dirección no existe"
            descripcion="El enlace puede estar mal escrito o la pantalla ya no está disponible."
            accion={
              <Link
                to="/"
                className="rounded-[6px] border border-linea-fuerte px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
              >
                Ir al inicio
              </Link>
            }
          />
        </CardBody>
      </Card>
    </div>
  );
}
