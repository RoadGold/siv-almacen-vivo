import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Field,
  Input,
  LoadingBlock,
  Modal,
  Notice,
  Select,
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHeader,
  TableHead,
  TableRow,
  useToast,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import { adminApi } from '@/shared/api/endpoints';
import { formatearFechaHora } from '@/shared/format/formato';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import type { Usuario } from '@/shared/types/api';

const ROLES = [
  { valor: 'administrador', texto: 'Administrador' },
  { valor: 'vendedor', texto: 'Vendedor' },
];

interface DatosAlta {
  nombre: string;
  usuario: string;
  password: string;
  rol: string;
  activo: boolean;
}

interface DatosEdicion {
  nombre?: string;
  password?: string;
  rol?: string;
  activo?: boolean;
}

/** Panel de administración de usuarios y roles. */
export function PanelUsuarios() {
  const [pagina, setPagina] = useState(1);
  const [filtroActivo, setFiltroActivo] = useState('');
  const [formulario, setFormulario] = useState<{ usuario: Usuario | null } | null>(null);

  const cliente = useQueryClient();
  const { notificar } = useToast();

  const listado = useQuery({
    queryKey: claves.admin.usuarios({ pagina, activo: filtroActivo || null }),
    queryFn: () =>
      adminApi.usuarios({
        pagina,
        tamano: 20,
        activo: filtroActivo === '' ? null : filtroActivo === 'activos',
      }),
  });

  const crear = useMutation({
    mutationFn: (datos: DatosAlta) => adminApi.crearUsuario(datos),
    onSuccess: (usuario) => {
      setFormulario(null);
      registrarOperacion(`Alta del usuario ${usuario.usuario}`);
      notificar(`Usuario «${usuario.nombre}» creado.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['admin'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const actualizar = useMutation({
    mutationFn: (datos: { id: number; cambios: DatosEdicion }) =>
      adminApi.actualizarUsuario(datos.id, datos.cambios),
    onSuccess: (usuario) => {
      setFormulario(null);
      registrarOperacion(`Actualización del usuario ${usuario.usuario}`);
      notificar(`Usuario «${usuario.nombre}» actualizado.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['admin'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const datos = listado.data;
  const guardando = crear.isPending || actualizar.isPending;

  return (
    <Card titulo="Usuarios" subtitulo={`${datos?.total ?? 0} usuarios registrados`}>
      <CardBody className="flex flex-wrap items-end justify-between gap-3 pb-2">
        <div className="w-[220px]">
          <label htmlFor="admin-filtro-usuarios" className="mb-1 block text-sm font-semibold">
            Estado
          </label>
          <Select
            id="admin-filtro-usuarios"
            value={filtroActivo}
            onChange={(evento) => {
              setFiltroActivo(evento.target.value);
              setPagina(1);
            }}
          >
            <option value="">Todos</option>
            <option value="activos">Solo activos</option>
            <option value="inactivos">Solo inactivos</option>
          </Select>
        </div>
        <Button variante="primario" onClick={() => setFormulario({ usuario: null })}>
          Nuevo usuario
        </Button>
      </CardBody>

      {listado.isError ? (
        <div className="p-4">
          <Notice tono="error" titulo="No se pudieron cargar los usuarios">
            {esSinPermisos(listado.error)
              ? 'No tienes permiso para administrar los usuarios.'
              : mensajeDeError(listado.error)}
          </Notice>
        </div>
      ) : listado.isLoading ? (
        <LoadingBlock etiqueta="Cargando usuarios…" />
      ) : (datos?.items.length ?? 0) === 0 ? (
        <EmptyState titulo="No hay usuarios que coincidan" />
      ) : (
        <Table descripcion="Usuarios del sistema">
          <TableHead>
            <TableHeader>Nombre</TableHeader>
            <TableHeader>Usuario</TableHeader>
            <TableHeader>Roles</TableHeader>
            <TableHeader>Último acceso</TableHeader>
            <TableHeader>Estado</TableHeader>
            <TableHeader>Acciones</TableHeader>
          </TableHead>
          <TableBody>
            {datos?.items.map((usuario) => (
              <TableRow key={usuario.id}>
                <TableCell className="font-semibold text-ink">{usuario.nombre}</TableCell>
                <TableCell className="numero text-xs">{usuario.usuario}</TableCell>
                <TableCell>
                  <span className="flex flex-wrap gap-1">
                    {usuario.roles.length === 0 ? (
                      <span className="text-xs text-muted">sin rol</span>
                    ) : (
                      usuario.roles.map((rol) => (
                        <Badge key={rol} tono="marca">
                          {rol}
                        </Badge>
                      ))
                    )}
                  </span>
                </TableCell>
                <TableCell className="numero text-xs">
                  {usuario.ultimo_acceso ? formatearFechaHora(usuario.ultimo_acceso) : 'nunca'}
                </TableCell>
                <TableCell>
                  <Badge tono={usuario.activo ? 'marca' : 'neutro'}>
                    {usuario.activo ? 'Activo' : 'Desactivado'}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button
                      variante="secundario"
                      tamano="sm"
                      onClick={() => setFormulario({ usuario })}
                    >
                      Editar
                    </Button>
                    <Button
                      variante="secundario"
                      tamano="sm"
                      disabled={actualizar.isPending}
                      onClick={() =>
                        actualizar.mutate({
                          id: usuario.id,
                          cambios: { activo: !usuario.activo },
                        })
                      }
                    >
                      {usuario.activo ? 'Desactivar' : 'Activar'}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <td className="px-3 py-2 text-xs text-muted" colSpan={5}>
              Página {datos?.pagina} de {datos?.paginas || 1} · {datos?.total ?? 0} usuarios
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

      {/* El formulario se monta de nuevo en cada apertura para tomar los datos del usuario. */}
      {formulario !== null ? (
        <ModalUsuario
          usuario={formulario.usuario}
          abierto
          guardando={guardando}
          onCerrar={() => setFormulario(null)}
          onGuardar={(alta, edicion) => {
            if (formulario.usuario) {
              actualizar.mutate({ id: formulario.usuario.id, cambios: edicion });
            } else {
              crear.mutate(alta);
            }
          }}
        />
      ) : null}
    </Card>
  );
}

/** Formulario de alta y edición de usuarios. */
function ModalUsuario({
  usuario,
  abierto,
  guardando,
  onCerrar,
  onGuardar,
}: {
  usuario: Usuario | null;
  abierto: boolean;
  guardando: boolean;
  onCerrar: () => void;
  onGuardar: (alta: DatosAlta, edicion: DatosEdicion) => void;
}) {
  const [nombre, setNombre] = useState(usuario?.nombre ?? '');
  const [nombreUsuario, setNombreUsuario] = useState(usuario?.usuario ?? '');
  const [password, setPassword] = useState('');
  const [rol, setRol] = useState(usuario?.roles[0] ?? 'vendedor');
  const [activo, setActivo] = useState(usuario?.activo ?? true);

  const esEdicion = usuario !== null;

  const errores: string[] = [];
  if (!nombre.trim()) errores.push('El nombre es obligatorio.');
  if (!esEdicion && !nombreUsuario.trim()) errores.push('El nombre de acceso es obligatorio.');
  if (!esEdicion && password.length < 6) {
    errores.push('La contraseña debe tener al menos 6 caracteres.');
  }
  if (esEdicion && password.length > 0 && password.length < 6) {
    errores.push('La nueva contraseña debe tener al menos 6 caracteres.');
  }

  return (
    <Modal
      abierto={abierto}
      titulo={esEdicion ? `Editar ${usuario.nombre}` : 'Nuevo usuario'}
      descripcion={
        esEdicion
          ? 'Deja la contraseña vacía para conservarla. Cambiar el rol elimina los roles anteriores.'
          : 'El rol define qué permisos tendrá el usuario en el sistema.'
      }
      onCerrar={onCerrar}
    >
      <div className="flex flex-col gap-4">
        <div className="grid gap-3 md:grid-cols-2">
          <Field htmlFor="usuario-nombre" etiqueta="Nombre completo" obligatorio>
            <Input
              id="usuario-nombre"
              value={nombre}
              onChange={(evento) => setNombre(evento.target.value)}
            />
          </Field>
          <Field htmlFor="usuario-acceso" etiqueta="Nombre de acceso" obligatorio>
            <Input
              id="usuario-acceso"
              value={nombreUsuario}
              disabled={esEdicion}
              onChange={(evento) => setNombreUsuario(evento.target.value)}
              placeholder="vendedor1"
            />
          </Field>
          <Field
            htmlFor="usuario-password"
            etiqueta={esEdicion ? 'Nueva contraseña' : 'Contraseña'}
            obligatorio={!esEdicion}
            ayuda={esEdicion ? 'Opcional: déjala vacía para no cambiarla.' : 'Mínimo 6 caracteres.'}
          >
            <Input
              id="usuario-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(evento) => setPassword(evento.target.value)}
            />
          </Field>
          <Field htmlFor="usuario-rol" etiqueta="Rol" obligatorio>
            <Select id="usuario-rol" value={rol} onChange={(evento) => setRol(evento.target.value)}>
              {ROLES.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.texto}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
          Usuario activo (puede iniciar sesión)
        </label>

        {errores.length > 0 ? (
          <Notice tono="aviso" titulo="Revisa el formulario">
            <ul className="list-disc pl-5">
              {errores.map((mensaje) => (
                <li key={mensaje}>{mensaje}</li>
              ))}
            </ul>
          </Notice>
        ) : null}

        <div className="flex flex-wrap justify-end gap-2 border-t border-linea pt-3">
          <Button variante="secundario" onClick={onCerrar}>
            Cancelar
          </Button>
          <Button
            variante="primario"
            cargando={guardando}
            textoCargando="Guardando…"
            disabled={errores.length > 0}
            onClick={() =>
              onGuardar(
                {
                  nombre: nombre.trim(),
                  usuario: nombreUsuario.trim(),
                  password,
                  rol,
                  activo,
                },
                {
                  nombre: nombre.trim(),
                  ...(password ? { password } : {}),
                  rol,
                  activo,
                },
              )
            }
          >
            Guardar usuario
          </Button>
        </div>
      </div>
    </Modal>
  );
}
