import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AvisoErrores,
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
import { catalogoApi } from '@/shared/api/endpoints';
import { Decimal } from '@/shared/format/decimal';
import { errorDeLongitud, reglaDe } from '@/shared/contrato/reglas';
import { formatearCantidad, formatearMoneda } from '@/shared/format/formato';
import { useRetraso } from '@/shared/hooks/useRetraso';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import { FormularioProducto, type DatosProductoFormulario } from './FormularioProducto';
import { ImportarCatalogo } from './ImportarCatalogo';
import type { Producto } from '@/shared/types/api';

/** Gestión de productos: catálogo paginado con búsqueda y alta/edición. */
export function Productos() {
  const { puede } = useAutenticacion();
  const [busqueda, setBusqueda] = useState('');
  const busquedaRetrasada = useRetraso(busqueda, 250);
  const [pagina, setPagina] = useState(1);
  const [modalAlta, setModalAlta] = useState(false);
  const [modalImportar, setModalImportar] = useState(false);
  const [productoEdicion, setProductoEdicion] = useState<Producto | null>(null);

  const cliente = useQueryClient();
  const { notificar } = useToast();

  const listado = useQuery({
    queryKey: claves.productos.listado({ q: busquedaRetrasada, pagina }),
    queryFn: () =>
      catalogoApi.listarProductos({
        q: busquedaRetrasada || undefined,
        pagina,
        tamano: 20,
      }),
  });

  const unidades = useQuery({
    queryKey: claves.productos.unidades,
    queryFn: () => catalogoApi.unidades(),
  });

  const categorias = useQuery({
    queryKey: claves.productos.categorias,
    queryFn: () => catalogoApi.categorias(),
  });

  const crear = useMutation({
    mutationFn: (datos: DatosProductoFormulario) =>
      catalogoApi.crearProducto({
        codigo: datos.codigo,
        nombre: datos.nombre,
        descripcion: datos.descripcion,
        categoria_id: datos.categoria_id,
        unidad_base_id: datos.unidad_base_id,
        stock_minimo_base: datos.stock_minimo_base,
        permite_fraccion: datos.permite_fraccion,
        activo: datos.activo,
        presentaciones: datos.presentaciones.map((item) => ({
          nombre: item.nombre,
          factor_base: item.factor_base,
          precio_venta: item.precio_venta,
          costo_referencia: item.costo_referencia,
          es_compra: item.es_compra,
          es_venta: item.es_venta,
          permite_fraccion: item.permite_fraccion,
        })),
      }),
    onSuccess: (producto) => {
      setModalAlta(false);
      registrarOperacion(`Alta de producto ${producto.codigo}`);
      notificar(`Producto «${producto.nombre}» creado.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['catalogo'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const actualizar = useMutation({
    mutationFn: (datos: {
      id: number;
      nombre: string;
      descripcion: string | null;
      stock_minimo_base: string;
      activo: boolean;
    }) =>
      catalogoApi.actualizarProducto(datos.id, {
        nombre: datos.nombre,
        descripcion: datos.descripcion,
        stock_minimo_base: datos.stock_minimo_base,
        activo: datos.activo,
      }),
    onSuccess: (producto) => {
      setProductoEdicion(null);
      registrarOperacion(`Edición de producto ${producto.codigo}`);
      notificar(`Producto «${producto.nombre}» actualizado.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['catalogo'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const datos = listado.data;

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="etiqueta">Gestionar</p>
          <h1 className="mt-1 text-2xl font-bold text-ink">Catálogo de productos</h1>
          <p className="mt-1 text-sm text-muted">
            Cada producto tiene una unidad base y presentaciones con equivalencias exactas.
          </p>
        </div>
        {puede('catalogo.gestionar') ? (
          <div className="flex flex-wrap gap-2">
            <Button variante="secundario" onClick={() => setModalImportar(true)}>
              Importar desde Excel
            </Button>
            <Button variante="primario" onClick={() => setModalAlta(true)}>
              Nuevo producto
            </Button>
          </div>
        ) : null}
      </header>

      <Card titulo="Productos" subtitulo={`${datos?.total ?? 0} registros`}>
        <CardBody className="pb-2">
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-[260px] flex-1">
              <Field
                htmlFor="buscador-productos"
                etiqueta="Buscar producto"
                ejemplo="Nombre, código o descripción…"
              >
                <Input
                  id="buscador-productos"
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
            <Notice tono="error" titulo="No se pudo cargar el catálogo">
              {esSinPermisos(listado.error)
                ? 'No tienes permiso para consultar el catálogo.'
                : mensajeDeError(listado.error)}
            </Notice>
          </div>
        ) : listado.isLoading ? (
          <LoadingBlock etiqueta="Cargando productos…" />
        ) : (datos?.items.length ?? 0) === 0 ? (
          <EmptyState
            titulo="No hay productos que coincidan"
            descripcion="Ajusta la búsqueda o crea el primer producto del catálogo."
          />
        ) : (
          <Table descripcion="Catálogo de productos">
            <TableHead>
              <TableHeader>Código</TableHeader>
              <TableHeader>Producto</TableHeader>
              <TableHeader>Unidad base</TableHeader>
              <TableHeader className="text-right">Mínimo</TableHeader>
              <TableHeader className="text-right">Presentaciones</TableHeader>
              <TableHeader>Estado</TableHeader>
              <TableHeader>Acciones</TableHeader>
            </TableHead>
            <TableBody>
              {datos?.items.map((producto) => (
                <TableRow key={producto.id}>
                  <TableCell className="numero text-xs text-muted">{producto.codigo}</TableCell>
                  <TableCell>
                    <span className="font-semibold text-ink">{producto.nombre}</span>
                    {producto.categoria ? (
                      <span className="ml-2 text-xs text-muted">{producto.categoria}</span>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-xs">{producto.unidad_base ?? '—'}</TableCell>
                  <TableCell numerica className="text-xs">
                    {formatearCantidad(producto.stock_minimo_base)}
                  </TableCell>
                  <TableCell numerica className="text-xs">
                    {producto.presentaciones.filter((item) => item.activo).length}
                  </TableCell>
                  <TableCell>
                    <Badge tono={producto.activo ? 'marca' : 'neutro'}>
                      {producto.activo ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {puede('catalogo.gestionar') ? (
                      <Button
                        variante="secundario"
                        tamano="sm"
                        onClick={() => setProductoEdicion(producto)}
                      >
                        Editar
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <td className="px-3 py-2 text-xs text-muted" colSpan={6}>
                Página {datos?.pagina} de {datos?.paginas || 1} · {datos?.total ?? 0} productos
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

      {/* --- Importación desde Excel --- */}
      {modalImportar ? (
        <ImportarCatalogo abierto onCerrar={() => setModalImportar(false)} />
      ) : null}

      {/* --- Alta de producto --- */}
      <Modal
        abierto={modalAlta}
        titulo="Nuevo producto"
        descripcion="Define la unidad base y las presentaciones con su equivalencia exacta."
        ancho="xl"
        onCerrar={() => setModalAlta(false)}
      >
        {unidades.isLoading || categorias.isLoading ? (
          <LoadingBlock etiqueta="Cargando catálogos base…" />
        ) : (
          <FormularioProducto
            unidades={unidades.data ?? []}
            categorias={categorias.data ?? []}
            guardando={crear.isPending}
            error={crear.isError ? crear.error : null}
            onCancelar={() => setModalAlta(false)}
            onEnviar={(datos) => crear.mutate(datos)}
          />
        )}
      </Modal>

      {/* --- Edición de producto --- */}
      <Modal
        abierto={productoEdicion !== null}
        titulo={`Editar ${productoEdicion?.nombre ?? ''}`}
        descripcion="Los cambios de precio y factor no alteran las operaciones ya confirmadas."
        onCerrar={() => setProductoEdicion(null)}
      >
        {productoEdicion ? (
          <FormularioEdicion
            producto={productoEdicion}
            guardando={actualizar.isPending}
            error={actualizar.isError ? actualizar.error : null}
            onCancelar={() => setProductoEdicion(null)}
            onEnviar={(datos) => actualizar.mutate({ id: productoEdicion.id, ...datos })}
          />
        ) : null}
      </Modal>
    </div>
  );
}

function FormularioEdicion({
  producto,
  onCancelar,
  onEnviar,
  guardando,
  error,
}: {
  producto: Producto;
  onCancelar: () => void;
  onEnviar: (datos: {
    nombre: string;
    descripcion: string | null;
    stock_minimo_base: string;
    activo: boolean;
  }) => void;
  guardando: boolean;
  error: unknown;
}) {
  const [nombre, setNombre] = useState(producto.nombre);
  const [descripcion, setDescripcion] = useState(producto.descripcion ?? '');
  const [stockMinimo, setStockMinimo] = useState(producto.stock_minimo_base);
  const [activo, setActivo] = useState(producto.activo);

  // Las mismas reglas que aplica el backend (ver `ProductoUpdate`).
  const errores: string[] = [];
  if (!nombre.trim()) errores.push('El nombre es obligatorio.');
  else {
    const error = errorDeLongitud(nombre, reglaDe('productos_edicion', 'nombre'), 'El nombre');
    if (error) errores.push(error);
  }
  const stockNumero = Decimal.intentarDesde(stockMinimo);
  if (stockNumero === null) {
    errores.push('El stock mínimo debe ser un número.');
  } else if (stockNumero.comparar(0) < 0) {
    errores.push('El stock mínimo no puede ser negativo.');
  }

  return (
    <div className="flex flex-col gap-4">
      {error ? (
        <AvisoErrores error={error} titulo="No se pudo guardar el producto" />
      ) : null}

      {errores.length > 0 ? (
        <Notice tono="error" titulo="Revise los datos antes de guardar">
          <ul className="list-disc pl-5">
            {errores.map((mensaje) => (
              <li key={mensaje}>{mensaje}</li>
            ))}
          </ul>
        </Notice>
      ) : null}

      <Field
        htmlFor="edicion-nombre"
        etiqueta="Nombre"
        ejemplo="Arroz a granel"
        obligatorio
        error={!nombre.trim() ? 'El nombre es obligatorio.' : undefined}
      >
        <Input
          id="edicion-nombre"
          invalido={!nombre.trim()}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
      </Field>

      <Field
        htmlFor="edicion-descripcion"
        etiqueta="Descripción"
        ejemplo="Arroz pilado de la marca Genérica"
      >
        <Input
          id="edicion-descripcion"
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
        />
      </Field>

      <Field
        htmlFor="edicion-stock-minimo"
        etiqueta="Stock mínimo"
        ejemplo="10000"
        ayuda={`Expresado en ${(producto.unidad_base ?? 'unidad base').toLowerCase()}.`}
        error={
          stockNumero === null
            ? 'El stock mínimo debe ser un número.'
            : stockNumero.comparar(0) < 0
              ? 'El stock mínimo no puede ser negativo.'
              : undefined
        }
      >
        <Input
          id="edicion-stock-minimo"
          className="numero"
          inputMode="decimal"
          invalido={stockNumero === null || stockNumero.comparar(0) < 0}
          value={stockMinimo}
          onChange={(e) => setStockMinimo(e.target.value)}
        />
      </Field>

      <label className="flex items-center gap-2 text-sm text-ink">
        <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
        Producto activo (disponible en el punto de venta)
      </label>

      <section>
        <h3 className="etiqueta mb-1">Presentaciones actuales</h3>
        {producto.presentaciones.length === 0 ? (
          <p className="text-sm text-muted">Este producto no tiene presentaciones registradas.</p>
        ) : (
          <ul className="divide-y divide-linea text-sm">
            {producto.presentaciones.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-1.5">
                <span className="text-ink">
                  {item.nombre}
                  <span className="ml-2 text-xs text-muted">
                    1 = {formatearCantidad(item.factor_base)}{' '}
                    {(producto.unidad_base ?? 'und').toLowerCase()}
                  </span>
                </span>
                <span className="numero text-ink">{formatearMoneda(item.precio_venta)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

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
              nombre: nombre.trim(),
              descripcion: descripcion.trim() || null,
              stock_minimo_base: (Decimal.intentarDesde(stockMinimo)?.aTexto() ?? '0'),
              activo,
            })
          }
        >
          Guardar cambios
        </Button>
      </div>
    </div>
  );
}
