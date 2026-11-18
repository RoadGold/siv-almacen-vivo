import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Field,
  LoadingBlock,
  Notice,
  Select,
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHeader,
  TableHead,
  TableRow,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import { adminApi } from '@/shared/api/endpoints';
import { formatearFechaHora } from '@/shared/format/formato';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';

const ENTIDADES = [
  { valor: '', texto: 'Todas las entidades' },
  { valor: 'venta', texto: 'Ventas' },
  { valor: 'abastecimiento', texto: 'Abastecimientos' },
  { valor: 'usuario', texto: 'Usuarios' },
  { valor: 'producto', texto: 'Productos' },
  { valor: 'proveedor', texto: 'Proveedores' },
  { valor: 'ajuste', texto: 'Ajustes' },
];

/** Panel de auditoría: registro de acciones sensibles (plan §5.8). */
export function PanelAuditoria() {
  const [entidad, setEntidad] = useState('');
  const [pagina, setPagina] = useState(1);

  const auditoria = useQuery({
    queryKey: claves.admin.auditoria({ entidad: entidad || null, pagina }),
    queryFn: () => adminApi.auditoria({ entidad: entidad || null, pagina, tamano: 50 }),
  });

  const datos = auditoria.data;

  return (
    <Card
      titulo="Auditoría"
      subtitulo="Registro de acciones sensibles: altas, anulaciones, ajustes y cambios de precio"
    >
      <CardBody className="flex flex-wrap items-end gap-3 pb-2">
        <div className="w-[240px]">
          <Field
            htmlFor="admin-filtro-auditoria"
            etiqueta="Entidad"
            ayuda="Ejemplo: venta, usuario o ajuste."
          >
            <Select
              id="admin-filtro-auditoria"
              value={entidad}
              onChange={(evento) => {
                setEntidad(evento.target.value);
                setPagina(1);
              }}
            >
              {ENTIDADES.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.texto}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </CardBody>

      {auditoria.isError ? (
        <div className="p-4">
          <Notice tono="error" titulo="No se pudo cargar la auditoría">
            {esSinPermisos(auditoria.error)
              ? 'No tienes permiso para consultar la auditoría.'
              : mensajeDeError(auditoria.error)}
          </Notice>
        </div>
      ) : auditoria.isLoading ? (
        <LoadingBlock etiqueta="Cargando auditoría…" />
      ) : (datos?.items.length ?? 0) === 0 ? (
        <EmptyState
          titulo="Sin registros de auditoría"
          descripcion="Todavía no hay acciones sensibles registradas para este filtro."
        />
      ) : (
        <Table descripcion="Registro de auditoría">
          <TableHead>
            <TableHeader>Fecha</TableHeader>
            <TableHeader>Acción</TableHeader>
            <TableHeader>Entidad</TableHeader>
            <TableHeader>Actor</TableHeader>
            <TableHeader>Detalle</TableHeader>
          </TableHead>
          <TableBody>
            {datos?.items.map((registro) => (
              <TableRow key={registro.id}>
                <TableCell className="numero text-xs">{formatearFechaHora(registro.created_at)}</TableCell>
                <TableCell>
                  <Badge tono="marca">{registro.accion}</Badge>
                </TableCell>
                <TableCell className="text-xs">
                  {registro.entidad}
                  {registro.entidad_id ? (
                    <span className="ml-1 text-muted">#{registro.entidad_id}</span>
                  ) : null}
                </TableCell>
                <TableCell className="numero text-xs">
                  {registro.actor_id ?? 'sistema'}
                </TableCell>
                <TableCell className="text-xs text-muted">
                  {registro.detalle ? JSON.stringify(registro.detalle) : '—'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <td className="px-3 py-2 text-xs text-muted" colSpan={4}>
              Página {datos?.pagina} de {datos?.paginas || 1} · {datos?.total ?? 0} registros
            </td>
            <td className="px-3 py-2">
              <div className="flex justify-end gap-2">
                <Button
                  variante="secundario"
                  tamano="sm"
                  disabled={pagina <= 1}
                  onClick={() => setPagina((actual) => Math.max(1, actual - 1))}
                >
                  Anterior
                </Button>
                <Button
                  variante="secundario"
                  tamano="sm"
                  disabled={pagina >= (datos?.paginas ?? 1)}
                  onClick={() => setPagina((actual) => actual + 1)}
                >
                  Siguiente
                </Button>
              </div>
            </td>
          </TableFooter>
        </Table>
      )}
    </Card>
  );
}
