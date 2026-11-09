import { Link } from 'react-router-dom';
import { Card, CardBody, EmptyState } from '@/design-system';

/**
 * Pantalla ANALIZAR: los reportes se habilitan en la siguiente fase.
 * Se deja navegable para no romper el mapa de navegación del plan §3.
 */
export function Analizar() {
  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="etiqueta">Analizar</p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Reportes</h1>
        <p className="mt-1 text-sm text-muted">
          Ventas por periodo, valor del inventario y margen bruto estimado.
        </p>
      </header>

      <Card titulo="Reportes">
        <CardBody>
          <EmptyState
            titulo="Esta sección está en construcción"
            descripcion="Los reportes se habilitarán en la próxima fase del plan. Por ahora puedes revisar las existencias y el radar de reposición."
            sugerencia="Los datos de origen ya están disponibles en el panel de Inicio y en Explorar."
            accion={
              <Link
                to="/explorar"
                className="rounded-[6px] border border-linea-fuerte px-4 py-2 text-sm font-semibold text-ink hover:border-brand hover:text-brand"
              >
                Ir a Explorar
              </Link>
            }
          />
        </CardBody>
      </Card>
    </div>
  );
}
