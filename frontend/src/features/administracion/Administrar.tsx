import { Link } from 'react-router-dom';
import { Card, CardBody, EmptyState } from '@/design-system';

/**
 * Pantalla ADMINISTRAR: usuarios, respaldos y auditoría del servidor local.
 * Se habilita en una fase posterior; queda navegable para conservar el mapa.
 */
export function Administrar() {
  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="etiqueta">Administrar</p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Administración del sistema</h1>
        <p className="mt-1 text-sm text-muted">
          Usuarios y roles, auditoría de acciones sensibles y copias de seguridad.
        </p>
      </header>

      <Card titulo="Administración">
        <CardBody>
          <EmptyState
            titulo="Esta sección está en construcción"
            descripcion="La gestión de usuarios y respaldos se habilitará en una fase posterior."
            sugerencia="El backend ya expone los endpoints /admin/usuarios y /admin/auditoria."
            accion={
              <Link
                to="/"
                className="rounded-[6px] border border-linea-fuerte px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
              >
                Volver al inicio
              </Link>
            }
          />
        </CardBody>
      </Card>
    </div>
  );
}
