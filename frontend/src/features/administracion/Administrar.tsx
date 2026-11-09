import { useState } from 'react';
import { Card, CardBody, Notice } from '@/design-system';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import { PanelAuditoria } from './PanelAuditoria';
import { PanelDiagnostico } from './PanelDiagnostico';
import { PanelUsuarios } from './PanelUsuarios';

type Seccion = 'usuarios' | 'auditoria' | 'diagnostico';

const SECCIONES: { id: Seccion; titulo: string }[] = [
  { id: 'usuarios', titulo: 'Usuarios y roles' },
  { id: 'auditoria', titulo: 'Auditoría' },
  { id: 'diagnostico', titulo: 'Diagnóstico del servidor' },
];

/**
 * Pantalla ADMINISTRAR: usuarios, auditoría y diagnóstico del servidor local.
 */
export function Administrar() {
  const { usuario, puede } = useAutenticacion();
  const [seccionElegida, setSeccionElegida] = useState<Seccion | null>(null);

  const seccionesVisibles = SECCIONES.filter((item) => {
    if (item.id === 'usuarios') return puede('admin.usuarios');
    if (item.id === 'auditoria') return puede('admin.auditoria');
    return true;
  });

  // Si el usuario no puede ver la sección elegida, se muestra la primera disponible.
  const seccion =
    seccionElegida && seccionesVisibles.some((item) => item.id === seccionElegida)
      ? seccionElegida
      : (seccionesVisibles[0]?.id ?? 'diagnostico');

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="etiqueta">Administrar</p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Administración del sistema</h1>
        <p className="mt-1 text-sm text-muted">
          Usuarios y roles, registro de acciones sensibles y estado del servidor local.
        </p>
      </header>

      {!puede('admin.usuarios') ? (
        <Notice tono="aviso" titulo="Acceso limitado">
          Tu rol no tiene el permiso «admin.usuarios»: no puedes crear ni modificar usuarios.
        </Notice>
      ) : null}

      <div
        className="flex flex-wrap items-center gap-1 rounded-[6px] border border-linea bg-surface p-1"
        role="tablist"
        aria-label="Secciones de administración"
      >
        {seccionesVisibles.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={seccion === item.id}
            onClick={() => setSeccionElegida(item.id)}
            className={[
              'rounded-[4px] px-4 py-1.5 text-sm font-semibold transition-colors',
              seccion === item.id ? 'bg-brand text-white' : 'text-muted hover:text-brand',
            ].join(' ')}
          >
            {item.titulo}
          </button>
        ))}
      </div>

      {seccion === 'usuarios' && puede('admin.usuarios') ? (
        <PanelUsuarios />
      ) : null}
      {seccion === 'auditoria' && puede('admin.auditoria') ? (
        <PanelAuditoria />
      ) : null}
      {seccion === 'diagnostico' ? <PanelDiagnostico /> : null}

      {seccion === 'usuarios' && !puede('admin.usuarios') ? (
        <Card titulo="Usuarios">
          <CardBody>
            <p className="text-sm text-muted">
              Necesitas el permiso «admin.usuarios» para consultar esta sección. El usuario
              activo es {usuario?.nombre} ({usuario?.usuario}).
            </p>
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}
