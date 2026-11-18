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
import { catalogoApi, proveedoresApi } from '@/shared/api/endpoints';
import { formatearFecha, formatearMoneda } from '@/shared/format/formato';
import { useRetraso } from '@/shared/hooks/useRetraso';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import type { Proveedor } from '@/shared/types/api';

/** Gestión de proveedores: listado, alta, edición y vinculación de productos. */
export function Proveedores() {
  const { puede } = useAutenticacion();
  const [busqueda, setBusqueda] = useState('');
  const busquedaRetrasada = useRetraso(busqueda, 250);
  const [pagina, setPagina] = useState(1);
  const [modalAlta, setModalAlta] = useState(false);
  const [proveedorEdicion, setProveedorEdicion] = useState<Proveedor | null>(null);
  const [proveedorVinculo, setProveedorVinculo] = useState<Proveedor | null>(null);

  const cliente = useQueryClient();
  const { notificar } = useToast();

  const listado = useQuery({
    queryKey: claves.proveedores.listado({ q: busquedaRetrasada, pagina }),
    queryFn: () =>
      proveedoresApi.listar({
        q: busquedaRetrasada || undefined,
        pagina,
        tamano: 20,
      }),
  });

  const crear = useMutation({
    mutationFn: (datos: {
      codigo: string;
      razon_social: string;
      nombre_comercial: string | null;
      ruc: string | null;
      telefono: string | null;
      contacto: string | null;
      direccion: string | null;
      email: string | null;
      observaciones: string | null;
      activo: boolean;
    }) => proveedoresApi.crear(datos),
    onSuccess: (proveedor) => {
      setModalAlta(false);
      registrarOperacion(`Alta de proveedor ${proveedor.codigo}`);
      notificar(`Proveedor «${proveedor.razon_social}» creado.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['proveedores'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const actualizar = useMutation({
    mutationFn: ({ id, codigo: _codigo, ...cambios }: {
      id: number;
      codigo: string;
      razon_social: string;
      nombre_comercial: string | null;
      ruc: string | null;
      telefono: string | null;
      contacto: string | null;
      direccion: string | null;
      email: string | null;
      observaciones: string | null;
      activo: boolean;
    }) => proveedoresApi.actualizar(id, cambios),
    onSuccess: (proveedor) => {
      setProveedorEdicion(null);
      registrarOperacion(`Edición de proveedor ${proveedor.codigo}`);
      notificar(`Proveedor «${proveedor.razon_social}» actualizado.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['proveedores'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const vincular = useMutation({
    mutationFn: (datos: {
      producto_id: number;
      proveedor_id: number;
      habitual: boolean;
      presentacion_id: number | null;
    }) => proveedoresApi.vincularProducto(datos),
    onSuccess: () => {
      setProveedorVinculo(null);
      registrarOperacion('Vinculación de producto con proveedor');
      notificar('Producto vinculado al proveedor.', 'exito');
      cliente.invalidateQueries({ queryKey: ['proveedores'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const datos = listado.data;

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="etiqueta">Gestionar</p>
          <h1 className="mt-1 text-2xl font-bold text-ink">Proveedores</h1>
          <p className="mt-1 text-sm text-muted">
            Un producto puede tener varios proveedores; el radar de reposición sugiere el mejor.
          </p>
        </div>
        {puede('proveedores.gestionar') ? (
          <Button variante="primario" onClick={() => setModalAlta(true)}>
            Nuevo proveedor
          </Button>
        ) : null}
      </header>

      <Card titulo="Directorio de proveedores" subtitulo={`${datos?.total ?? 0} registros`}>
        <CardBody className="pb-2">
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-[260px] flex-1">
              <Field
                htmlFor="buscador-proveedores"
                etiqueta="Buscar proveedor"
                ejemplo="Razón social, código, RUC o contacto…"
              >
                <Input
                  id="buscador-proveedores"
                  value={busqueda}
                  onChange={(evento) => {
                    setBusqueda(evento.target.value);
                    setPagina(1);
                  }}
                  autoComplete="off"
                />
              </Field>
            </div>
          </div>
        </CardBody>

        {listado.isError ? (
          <div className="p-4">
            <Notice tono="error" titulo="No se pudieron cargar los proveedores">
              {esSinPermisos(listado.error)
                ? 'No tienes permiso para consultar los proveedores.'
                : mensajeDeError(listado.error)}
            </Notice>
          </div>
        ) : listado.isLoading ? (
          <LoadingBlock etiqueta="Cargando proveedores…" />
        ) : (datos?.items.length ?? 0) === 0 ? (
          <EmptyState
            titulo="No hay proveedores que coincidan"
            descripcion="Ajusta la búsqueda o registra el primer proveedor."
          />
        ) : (
          <Table descripcion="Directorio de proveedores">
            <TableHead>
              <TableHeader>Código</TableHeader>
              <TableHeader>Razón social</TableHeader>
              <TableHeader>Contacto</TableHeader>
              <TableHeader>RUC</TableHeader>
              <TableHeader>Estado</TableHeader>
              <TableHeader>Acciones</TableHeader>
            </TableHead>
            <TableBody>
              {datos?.items.map((proveedor) => (
                <TableRow key={proveedor.id}>
                  <TableCell className="numero text-xs text-muted">{proveedor.codigo}</TableCell>
                  <TableCell>
                    <span className="font-semibold text-ink">{proveedor.razon_social}</span>
                    {proveedor.nombre_comercial ? (
                      <span className="ml-2 text-xs text-muted">{proveedor.nombre_comercial}</span>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-xs">
                    {proveedor.contacto ?? '—'}
                    {proveedor.telefono ? (
                      <span className="ml-2 text-muted">{proveedor.telefono}</span>
                    ) : null}
                  </TableCell>
                  <TableCell className="numero text-xs">{proveedor.ruc ?? '—'}</TableCell>
                  <TableCell>
                    <Badge tono={proveedor.activo ? 'marca' : 'neutro'}>
                      {proveedor.activo ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {puede('proveedores.gestionar') ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          variante="secundario"
                          tamano="sm"
                          onClick={() => setProveedorVinculo(proveedor)}
                        >
                          Vincular producto
                        </Button>
                        <Button
                          variante="secundario"
                          tamano="sm"
                          onClick={() => setProveedorEdicion(proveedor)}
                        >
                          Editar
                        </Button>
                      </div>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <td className="px-3 py-2 text-xs text-muted" colSpan={5}>
                Página {datos?.pagina} de {datos?.paginas || 1} · {datos?.total ?? 0} proveedores
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

      {/* --- Alta / edición --- */}
      <Modal
        abierto={modalAlta || proveedorEdicion !== null}
        titulo={proveedorEdicion ? `Editar ${proveedorEdicion.razon_social}` : 'Nuevo proveedor'}
        ancho="lg"
        onCerrar={() => {
          setModalAlta(false);
          setProveedorEdicion(null);
        }}
      >
        <FormularioProveedor
          proveedor={proveedorEdicion}
          guardando={crear.isPending || actualizar.isPending}
          error={
            crear.isError
              ? mensajeDeError(crear.error)
              : actualizar.isError
                ? mensajeDeError(actualizar.error)
                : null
          }
          onCancelar={() => {
            setModalAlta(false);
            setProveedorEdicion(null);
          }}
          onEnviar={(datos) => {
            if (proveedorEdicion) {
              actualizar.mutate({ id: proveedorEdicion.id, ...datos });
            } else {
              crear.mutate(datos);
            }
          }}
        />
      </Modal>

      {/* --- Vincular producto --- */}
      <Modal
        abierto={proveedorVinculo !== null}
        titulo={`Vincular producto · ${proveedorVinculo?.razon_social ?? ''}`}
        descripcion="El producto aparecerá como habitual en la pantalla de recepción."
        ancho="lg"
        onCerrar={() => setProveedorVinculo(null)}
      >
        {proveedorVinculo ? (
          <FormularioVinculo
            proveedorId={proveedorVinculo.id}
            guardando={vincular.isPending}
            error={vincular.isError ? mensajeDeError(vincular.error) : null}
            onCancelar={() => setProveedorVinculo(null)}
            onEnviar={(datos) => vincular.mutate({ ...datos, proveedor_id: proveedorVinculo.id })}
          />
        ) : null}
      </Modal>
    </div>
  );
}

/** Formulario de alta y edición de proveedor. */
function FormularioProveedor({
  proveedor,
  onCancelar,
  onEnviar,
  guardando,
  error,
}: {
  proveedor: Proveedor | null;
  onCancelar: () => void;
  onEnviar: (datos: {
    codigo: string;
    razon_social: string;
    nombre_comercial: string | null;
    ruc: string | null;
    telefono: string | null;
    contacto: string | null;
    direccion: string | null;
    email: string | null;
    observaciones: string | null;
    activo: boolean;
  }) => void;
  guardando: boolean;
  error: string | null;
}) {
  const [codigo, setCodigo] = useState(proveedor?.codigo ?? '');
  const [razonSocial, setRazonSocial] = useState(proveedor?.razon_social ?? '');
  const [nombreComercial, setNombreComercial] = useState(proveedor?.nombre_comercial ?? '');
  const [ruc, setRuc] = useState(proveedor?.ruc ?? '');
  const [telefono, setTelefono] = useState(proveedor?.telefono ?? '');
  const [contacto, setContacto] = useState(proveedor?.contacto ?? '');
  const [direccion, setDireccion] = useState(proveedor?.direccion ?? '');
  const [email, setEmail] = useState(proveedor?.email ?? '');
  const [observaciones, setObservaciones] = useState(proveedor?.observaciones ?? '');
  const [activo, setActivo] = useState(proveedor?.activo ?? true);

  const errores: string[] = [];
  if (!codigo.trim()) errores.push('El código es obligatorio.');
  if (!razonSocial.trim()) errores.push('La razón social es obligatoria.');
  if (email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
    errores.push('El correo electrónico no tiene un formato válido.');
  }

  return (
    <div className="flex flex-col gap-4">
      {error ? (
        <Notice tono="error" titulo="No se pudo guardar el proveedor">
          {error}
        </Notice>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        <Field htmlFor="proveedor-codigo" etiqueta="Código" ejemplo="PROV-001" obligatorio>
          <Input
            id="proveedor-codigo"
            value={codigo}
            disabled={Boolean(proveedor)}
            onChange={(evento) => setCodigo(evento.target.value)}
          />
        </Field>
        <Field
          htmlFor="proveedor-razon"
          etiqueta="Razón social"
          ejemplo="Distribuidora ABC S.A.C."
          obligatorio
        >
          <Input
            id="proveedor-razon"
            value={razonSocial}
            onChange={(evento) => setRazonSocial(evento.target.value)}
          />
        </Field>
        <Field
          htmlFor="proveedor-nombre-comercial"
          etiqueta="Nombre comercial"
          ejemplo="ABC"
        >
          <Input
            id="proveedor-nombre-comercial"
            value={nombreComercial}
            onChange={(evento) => setNombreComercial(evento.target.value)}
          />
        </Field>
        <Field htmlFor="proveedor-ruc" etiqueta="RUC" ejemplo="20123456789">
          <Input
            id="proveedor-ruc"
            className="numero"
            value={ruc}
            onChange={(evento) => setRuc(evento.target.value)}
          />
        </Field>
        <Field htmlFor="proveedor-telefono" etiqueta="Teléfono" ejemplo="01 555 0123">
          <Input
            id="proveedor-telefono"
            value={telefono}
            onChange={(evento) => setTelefono(evento.target.value)}
          />
        </Field>
        <Field
          htmlFor="proveedor-contacto"
          etiqueta="Persona de contacto"
          ejemplo="Carlos Ramos"
        >
          <Input
            id="proveedor-contacto"
            value={contacto}
            onChange={(evento) => setContacto(evento.target.value)}
          />
        </Field>
        <Field
          htmlFor="proveedor-email"
          etiqueta="Correo electrónico"
          ejemplo="compras@abc.com"
        >
          <Input
            id="proveedor-email"
            type="email"
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
          />
        </Field>
        <Field
          htmlFor="proveedor-direccion"
          etiqueta="Dirección"
          ejemplo="Av. Siempre Viva 742"
        >
          <Input
            id="proveedor-direccion"
            value={direccion}
            onChange={(evento) => setDireccion(evento.target.value)}
          />
        </Field>
      </div>

      <Field
        htmlFor="proveedor-observaciones"
        etiqueta="Observaciones"
        ejemplo="Entrega los martes por la mañana."
      >
        <Input
          id="proveedor-observaciones"
          value={observaciones}
          onChange={(evento) => setObservaciones(evento.target.value)}
        />
      </Field>

      <label className="flex items-center gap-2 text-sm text-ink">
        <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
        Proveedor activo (disponible para nuevas recepciones)
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
        <Button variante="secundario" onClick={onCancelar}>
          Cancelar
        </Button>
        <Button
          variante="primario"
          cargando={guardando}
          textoCargando="Guardando…"
          disabled={errores.length > 0}
          onClick={() =>
            onEnviar({
              codigo: codigo.trim(),
              razon_social: razonSocial.trim(),
              nombre_comercial: nombreComercial.trim() || null,
              ruc: ruc.trim() || null,
              telefono: telefono.trim() || null,
              contacto: contacto.trim() || null,
              direccion: direccion.trim() || null,
              email: email.trim() || null,
              observaciones: observaciones.trim() || null,
              activo,
            })
          }
        >
          Guardar proveedor
        </Button>
      </div>
    </div>
  );
}

/** Formulario para vincular un producto del catálogo con un proveedor. */
function FormularioVinculo({
  proveedorId,
  onCancelar,
  onEnviar,
  guardando,
  error,
}: {
  proveedorId: number;
  onCancelar: () => void;
  onEnviar: (datos: {
    producto_id: number;
    proveedor_id: number;
    habitual: boolean;
    presentacion_id: number | null;
  }) => void;
  guardando: boolean;
  error: string | null;
}) {
  const [busqueda, setBusqueda] = useState('');
  const busquedaRetrasada = useRetraso(busqueda, 250);
  const [productoId, setProductoId] = useState<number | null>(null);
  const [presentacionId, setPresentacionId] = useState<number | ''>('');
  const [habitual, setHabitual] = useState(true);

  const productos = useQuery({
    queryKey: claves.productos.listado({ q: busquedaRetrasada, vinculo: proveedorId }),
    queryFn: () =>
      catalogoApi.listarProductos({
        q: busquedaRetrasada || undefined,
        pagina: 1,
        tamano: 15,
      }),
  });

  const vinculos = useQuery({
    queryKey: claves.proveedores.productos(proveedorId),
    queryFn: () => proveedoresApi.productos(proveedorId),
  });

  const producto = productos.data?.items.find((item) => item.id === productoId);

  return (
    <div className="flex flex-col gap-4">
      {error ? (
        <Notice tono="error" titulo="No se pudo vincular el producto">
          {error}
        </Notice>
      ) : null}

      <Field
        htmlFor="vinculo-busqueda"
        etiqueta="Buscar producto del catálogo"
        ejemplo="Nombre o código…"
      >
        <Input
          id="vinculo-busqueda"
          value={busqueda}
          onChange={(evento) => setBusqueda(evento.target.value)}
          autoComplete="off"
        />
      </Field>

      {productos.isLoading ? (
        <LoadingBlock etiqueta="Buscando productos…" />
      ) : (productos.data?.items.length ?? 0) === 0 ? (
        <p className="text-sm text-muted">Sin resultados para esa búsqueda.</p>
      ) : (
        <ul className="max-h-56 divide-y divide-linea overflow-y-auto rounded-[6px] border border-linea">
          {productos.data?.items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => {
                  setProductoId(item.id);
                  setPresentacionId('');
                }}
                className={[
                  'flex w-full items-center justify-between px-3 py-2 text-left text-sm',
                  productoId === item.id ? 'bg-brand-tenue text-brand' : 'hover:bg-surface-tenue',
                ].join(' ')}
              >
                <span className="font-semibold text-ink">{item.nombre}</span>
                <span className="numero text-xs text-muted">{item.codigo}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {producto ? (
        <Field
          htmlFor="vinculo-presentacion"
          etiqueta="Presentación de compra (opcional)"
          ayuda="Ejemplo: Saco 50 kg."
        >
          <Select
            id="vinculo-presentacion"
            value={presentacionId}
            onChange={(evento) =>
              setPresentacionId(evento.target.value === '' ? '' : Number(evento.target.value))
            }
          >
            <option value="">Sin presentación fija</option>
            {producto.presentaciones
              .filter((item) => item.activo && item.es_compra)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre} · {formatearMoneda(item.costo_referencia)}
                </option>
              ))}
          </Select>
        </Field>
      ) : null}

      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={habitual}
          onChange={(evento) => setHabitual(evento.target.checked)}
        />
        Marcar como producto habitual de este proveedor
      </label>

      {vinculos.data && vinculos.data.length > 0 ? (
        <section>
          <h3 className="etiqueta mb-1">Productos ya vinculados</h3>
          <ul className="divide-y divide-linea text-sm">
            {vinculos.data.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-1.5">
                <span className="text-ink">{item.nombre}</span>
                <span className="text-xs text-muted">
                  {item.presentacion_nombre ?? 'Sin presentación fija'}
                  {item.ultima_fecha_compra
                    ? ` · última compra ${formatearFecha(item.ultima_fecha_compra)}`
                    : ''}
                  {item.ultimo_costo ? ` · ${formatearMoneda(item.ultimo_costo)}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="flex flex-wrap justify-end gap-2 border-t border-linea pt-3">
        <Button variante="secundario" onClick={onCancelar}>
          Cancelar
        </Button>
        <Button
          variante="primario"
          cargando={guardando}
          textoCargando="Vinculando…"
          disabled={productoId === null}
          onClick={() =>
            onEnviar({
              producto_id: productoId!,
              proveedor_id: proveedorId,
              habitual,
              presentacion_id: presentacionId === '' ? null : presentacionId,
            })
          }
        >
          Vincular
        </Button>
      </div>
    </div>
  );
}
