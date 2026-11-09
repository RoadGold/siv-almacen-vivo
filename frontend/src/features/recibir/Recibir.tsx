import { useMemo, useState } from 'react';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
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
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHead,
  TableRow,
  useToast,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import { abastecimientosApi, catalogoApi, proveedoresApi } from '@/shared/api/endpoints';
import { Decimal } from '@/shared/format/decimal';
import {
  formatearCantidad,
  formatearEnUnidadLegible,
  formatearFecha,
  formatearMoneda,
  hoyISO,
} from '@/shared/format/formato';
import { useRetraso } from '@/shared/hooks/useRetraso';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { FilaIngreso, type DatosLineaIngreso } from './FilaIngreso';
import type { Abastecimiento, PrevisualizacionAbastecimiento, Proveedor } from '@/shared/types/api';

const PASOS = [
  { numero: 1, titulo: 'Proveedor' },
  { numero: 2, titulo: 'Productos' },
  { numero: 3, titulo: 'Revisar y confirmar' },
];

/** Pantalla RECIBIR: ingreso de mercadería en tres pasos visibles. */
export function Recibir() {
  const [paso, setPaso] = useState(1);
  const [proveedor, setProveedor] = useState<Proveedor | null>(null);
  const [busquedaProveedor, setBusquedaProveedor] = useState('');
  const busquedaProveedorRetrasada = useRetraso(busquedaProveedor, 250);

  const [documento, setDocumento] = useState('');
  const [fecha, setFecha] = useState(hoyISO());
  const [observaciones, setObservaciones] = useState('');

  const [lineas, setLineas] = useState<DatosLineaIngreso[]>([]);
  const [busquedaProducto, setBusquedaProducto] = useState('');
  const busquedaProductoRetrasada = useRetraso(busquedaProducto, 250);

  const [previa, setPrevia] = useState<PrevisualizacionAbastecimiento | null>(null);
  const [modalImpacto, setModalImpacto] = useState(false);
  const [ingresoRegistrado, setIngresoRegistrado] = useState<Abastecimiento | null>(null);

  const cliente = useQueryClient();
  const { notificar } = useToast();

  const consultaProveedores = useQuery({
    queryKey: claves.proveedores.listado({ q: busquedaProveedorRetrasada }),
    queryFn: () =>
      proveedoresApi.listar({
        q: busquedaProveedorRetrasada || undefined,
        pagina: 1,
        tamano: 20,
      }),
  });

  const consultaProductosProveedor = useQuery({
    queryKey: claves.proveedores.productos(proveedor?.id ?? 0),
    queryFn: () => proveedoresApi.productos(proveedor!.id),
    enabled: Boolean(proveedor),
  });

  // Se necesitan las presentaciones de compra de cada producto habitual.
  const habituales = useMemo(
    () => (consultaProductosProveedor.data ?? []).slice(0, 30),
    [consultaProductosProveedor.data],
  );

  const detalleHabituales = useQueries({
    queries: habituales.map((item) => ({
      queryKey: claves.productos.detalle(item.producto_id),
      queryFn: () => catalogoApi.obtenerProducto(item.producto_id),
      staleTime: 5 * 60_000,
    })),
  });

  const consultaCatalogo = useQuery({
    queryKey: claves.productos.listado({ q: busquedaProductoRetrasada, extra: 'ingreso' }),
    queryFn: () =>
      catalogoApi.listarProductos({
        q: busquedaProductoRetrasada || undefined,
        pagina: 1,
        tamano: 12,
      }),
    enabled: paso === 2 && busquedaProductoRetrasada.trim().length > 0,
  });

  function agregarLinea(datos: DatosLineaIngreso) {
    setLineas((actuales) => {
      const existente = actuales.find(
        (item) =>
          item.producto_id === datos.producto_id &&
          item.presentacion_id === datos.presentacion_id,
      );
      if (!existente) return [...actuales, datos];
      return actuales.map((item) =>
        item === existente
          ? { ...item, cantidad: datos.cantidad, costo_unitario: datos.costo_unitario }
          : item,
      );
    });
  }

  function quitarLinea(indice: number) {
    setLineas((actuales) => actuales.filter((_, posicion) => posicion !== indice));
  }

  function cambiarCampoLinea(
    indice: number,
    campo: 'cantidad' | 'costo_unitario',
    valor: string,
  ) {
    setLineas((actuales) =>
      actuales.map((item, posicion) => (posicion === indice ? { ...item, [campo]: valor } : item)),
    );
  }

  const total = useMemo(
    () =>
      lineas.reduce(
        (acumulado, linea) =>
          acumulado.suma(Decimal.desde(linea.cantidad).multiplica(linea.costo_unitario)),
        Decimal.cero(),
      ),
    [lineas],
  );

  const impacto = useMemo(
    () =>
      lineas.map((linea) => ({
        id: `${linea.producto_id}-${linea.presentacion_id}`,
        texto: `${linea.producto_nombre} +${formatearCantidad(
          Decimal.desde(linea.cantidad).multiplica(linea.factor_base),
        )} ${linea.unidad_base?.toLowerCase() ?? 'und'}`,
      })),
    [lineas],
  );

  function cuerpoIngreso() {
    return {
      proveedor_id: proveedor!.id,
      fecha,
      documento: documento.trim() || null,
      observaciones: observaciones.trim() || null,
      lineas: lineas.map((linea) => ({
        producto_id: linea.producto_id,
        presentacion_id: linea.presentacion_id,
        cantidad: linea.cantidad,
        costo_unitario: linea.costo_unitario,
      })),
    };
  }

  const previsualizar = useMutation({
    mutationFn: () => abastecimientosApi.previsualizar(cuerpoIngreso()),
    onSuccess: (respuesta) => {
      setPrevia(respuesta);
      setModalImpacto(true);
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const confirmar = useMutation({
    mutationFn: () => abastecimientosApi.confirmar(cuerpoIngreso()),
    onSuccess: (ingreso) => {
      setIngresoRegistrado(ingreso);
      setModalImpacto(false);
      setPrevia(null);
      setLineas([]);
      setPaso(1);
      registrarOperacion(`Ingreso ${ingreso.numero}`);
      notificar(`Ingreso ${ingreso.numero} registrado correctamente.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['inventario'] });
      cliente.invalidateQueries({ queryKey: ['abastecimientos'] });
      cliente.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  function reiniciar() {
    setIngresoRegistrado(null);
    setProveedor(null);
    setLineas([]);
    setDocumento('');
    setObservaciones('');
    setPaso(1);
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="etiqueta">Estación · Recibir</p>
          <h1 className="mt-1 text-2xl font-bold text-ink">Recibir mercadería</h1>
          <p className="mt-1 text-sm text-muted">
            Elige el proveedor, registra los productos y revisa el impacto antes de confirmar.
          </p>
        </div>
        {ingresoRegistrado ? (
          <div className="flex flex-wrap gap-2">
            <Badge tono="marca">Ingreso {ingresoRegistrado.numero} confirmado</Badge>
            <Button variante="acento" onClick={reiniciar}>
              Nuevo ingreso
            </Button>
          </div>
        ) : null}
      </header>

      {/* --- Pasos visibles --- */}
      <ol className="flex flex-wrap items-center gap-2" aria-label="Pasos del ingreso">
        {PASOS.map((item, indice) => {
          const activo = paso === item.numero;
          const completado = paso > item.numero;
          return (
            <li key={item.numero} className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  if (item.numero === 1) setPaso(1);
                  if (item.numero === 2 && proveedor) setPaso(2);
                  if (item.numero === 3 && lineas.length > 0) setPaso(3);
                }}
                className={[
                  'flex items-center gap-2 rounded-[6px] border px-3 py-1.5 text-sm transition-colors',
                  activo
                    ? 'border-brand bg-brand text-white'
                    : completado
                      ? 'border-brand bg-brand-tenue text-brand'
                      : 'border-linea bg-surface text-muted',
                ].join(' ')}
                aria-current={activo ? 'step' : undefined}
              >
                <span className="font-bold numero">{item.numero}.</span>
                <span>{item.titulo}</span>
                {completado ? <span aria-hidden="true">✓</span> : null}
              </button>
              {indice < PASOS.length - 1 ? (
                <span aria-hidden="true" className="text-muted">
                  →
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>

      {/* --- Paso 1: proveedor --- */}
      {paso === 1 ? (
        <Card titulo="Paso 1 · Proveedor" subtitulo="Selecciona quién suministró la mercadería">
          <CardBody>
            <div className="mb-4 flex flex-wrap items-end gap-2">
              <div className="min-w-[260px] flex-1">
                <label htmlFor="buscador-proveedor" className="mb-1 block text-sm font-semibold">
                  Buscar proveedor
                </label>
                <Input
                  id="buscador-proveedor"
                  value={busquedaProveedor}
                  onChange={(evento) => setBusquedaProveedor(evento.target.value)}
                  placeholder="Razón social, código o RUC…"
                  autoComplete="off"
                />
              </div>
            </div>

            {consultaProveedores.isError ? (
              <Notice tono="error" titulo="No se pudieron cargar los proveedores">
                {esSinPermisos(consultaProveedores.error)
                  ? 'No tienes permiso para consultar los proveedores.'
                  : mensajeDeError(consultaProveedores.error)}
              </Notice>
            ) : consultaProveedores.isLoading ? (
              <LoadingBlock etiqueta="Cargando proveedores…" />
            ) : (consultaProveedores.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                titulo="No hay proveedores que coincidan"
                descripcion="Crea el proveedor en Gestionar → Proveedores si todavía no existe."
              />
            ) : (
              <ul className="divide-y divide-linea">
                {consultaProveedores.data?.items.map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-3 py-2">
                    <div>
                      <p className="text-sm font-semibold text-ink">
                        {item.razon_social}
                        {item.nombre_comercial ? (
                          <span className="ml-2 text-xs font-normal text-muted">
                            {item.nombre_comercial}
                          </span>
                        ) : null}
                      </p>
                      <p className="text-xs text-muted">
                        Código {item.codigo}
                        {item.ruc ? ` · RUC ${item.ruc}` : ''}
                        {item.telefono ? ` · ${item.telefono}` : ''}
                      </p>
                    </div>
                    <Button
                      variante="primario"
                      tamano="sm"
                      onClick={() => {
                        setProveedor(item);
                        setPaso(2);
                      }}
                    >
                      Elegir
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      ) : null}

      {/* --- Paso 2: productos --- */}
      {paso === 2 && proveedor ? (
        <div className="flex flex-col gap-4">
          <Card
            titulo="Paso 2 · Productos"
            subtitulo={`Proveedor: ${proveedor.razon_social}`}
            acciones={
              <Button variante="secundario" tamano="sm" onClick={() => setPaso(1)}>
                Cambiar proveedor
              </Button>
            }
          >
            <CardBody className="grid gap-4 md:grid-cols-3">
              <Field htmlFor="documento-ingreso" etiqueta="Documento de referencia">
                <Input
                  id="documento-ingreso"
                  value={documento}
                  onChange={(evento) => setDocumento(evento.target.value)}
                  placeholder="F001-00123"
                />
              </Field>
              <Field htmlFor="fecha-ingreso" etiqueta="Fecha">
                <Input
                  id="fecha-ingreso"
                  type="date"
                  className="numero"
                  value={fecha}
                  onChange={(evento) => setFecha(evento.target.value)}
                />
              </Field>
              <Field htmlFor="observaciones-ingreso" etiqueta="Observaciones">
                <Input
                  id="observaciones-ingreso"
                  value={observaciones}
                  onChange={(evento) => setObservaciones(evento.target.value)}
                  placeholder="Opcional"
                />
              </Field>
            </CardBody>
          </Card>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
            <div className="flex flex-col gap-4">
              <Card
                titulo="Sus productos habituales"
                subtitulo="Productos que este proveedor suele suministrar"
              >
                {consultaProductosProveedor.isLoading ? (
                  <LoadingBlock etiqueta="Cargando productos del proveedor…" />
                ) : consultaProductosProveedor.isError ? (
                  <div className="p-4">
                    <Notice tono="error" titulo="No se pudieron cargar los productos habituales">
                      {mensajeDeError(consultaProductosProveedor.error)}
                    </Notice>
                  </div>
                ) : habituales.length === 0 ? (
                  <EmptyState
                    titulo="Este proveedor no tiene productos habituales"
                    descripcion="Busca un producto del catálogo para añadirlo al ingreso."
                  />
                ) : (
                  <div>
                    {habituales.map((item, indice) => {
                      const detalle = detalleHabituales[indice]?.data;
                      const presentaciones =
                        detalle?.presentaciones ??
                        (item.presentacion_id
                          ? [
                              {
                                id: item.presentacion_id,
                                nombre: item.presentacion_nombre ?? 'Presentación',
                                factor_base: item.factor_base ?? '1',
                                precio_venta: '0',
                                costo_referencia: item.ultimo_costo ?? '0',
                                es_compra: true,
                                es_venta: true,
                                permite_fraccion: false,
                                activo: true,
                              },
                            ]
                          : []);
                      return (
                        <FilaIngreso
                          key={item.producto_id}
                          productoId={item.producto_id}
                          codigo={item.codigo}
                          nombre={item.nombre}
                          unidadBase={item.unidad_base}
                          presentaciones={presentaciones}
                          presentacionHabitualId={item.presentacion_id}
                          ultimoCosto={item.ultimo_costo}
                          yaAgregado={lineas.some((linea) => linea.producto_id === item.producto_id)}
                          onAgregar={agregarLinea}
                        />
                      );
                    })}
                  </div>
                )}
              </Card>

              <Card titulo="Buscar otro producto del catálogo" subtitulo="Agrega productos que no son habituales del proveedor">
                <CardBody>
                  <Input
                    value={busquedaProducto}
                    onChange={(evento) => setBusquedaProducto(evento.target.value)}
                    placeholder="Nombre o código del producto…"
                    aria-label="Buscar producto del catálogo para el ingreso"
                    autoComplete="off"
                  />

                  {consultaCatalogo.isLoading ? (
                    <div className="mt-3">
                      <LoadingBlock etiqueta="Buscando en el catálogo…" />
                    </div>
                  ) : consultaCatalogo.isError ? (
                    <div className="mt-3">
                      <Notice tono="error" titulo="No se pudo buscar en el catálogo">
                        {mensajeDeError(consultaCatalogo.error)}
                      </Notice>
                    </div>
                  ) : (consultaCatalogo.data?.items.length ?? 0) === 0 ? (
                    <p className="mt-3 text-sm text-muted">Sin resultados para esa búsqueda.</p>
                  ) : (
                    <ul className="mt-3 divide-y divide-linea border-t border-linea">
                      {consultaCatalogo.data?.items.map((producto) => (
                        <li key={producto.id} className="py-3">
                          <FilaIngreso
                            productoId={producto.id}
                            codigo={producto.codigo}
                            nombre={producto.nombre}
                            unidadBase={producto.unidad_base}
                            presentaciones={producto.presentaciones}
                            yaAgregado={lineas.some((linea) => linea.producto_id === producto.id)}
                            onAgregar={agregarLinea}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                </CardBody>
              </Card>
            </div>

            <Card titulo="Resumen del ingreso" subtitulo={`${lineas.length} línea(s)`}>
              {lineas.length === 0 ? (
                <EmptyState
                  titulo="Sin líneas todavía"
                  descripcion="Añade productos desde la lista habitual o desde el catálogo."
                />
              ) : (
                <ul className="divide-y divide-linea">
                  {lineas.map((linea, indice) => (
                    <li key={`${linea.producto_id}-${linea.presentacion_id}`} className="px-4 py-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-ink">
                            {linea.producto_nombre}
                          </p>
                          <p className="text-xs text-muted">{linea.presentacion_nombre}</p>
                        </div>
                        <Button
                          variante="fantasma"
                          tamano="sm"
                          onClick={() => quitarLinea(indice)}
                          aria-label={`Quitar ${linea.producto_nombre}`}
                        >
                          Quitar
                        </Button>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <div className="w-[88px]">
                          <label htmlFor={`cantidad-linea-${indice}`} className="sr-only">
                            Cantidad de {linea.producto_nombre}
                          </label>
                          <Input
                            id={`cantidad-linea-${indice}`}
                            className="numero"
                            inputMode="decimal"
                            value={linea.cantidad}
                            onChange={(evento) =>
                              cambiarCampoLinea(indice, 'cantidad', evento.target.value)
                            }
                          />
                        </div>
                        <div className="w-[110px]">
                          <label htmlFor={`costo-linea-${indice}`} className="sr-only">
                            Costo unitario de {linea.producto_nombre}
                          </label>
                          <Input
                            id={`costo-linea-${indice}`}
                            className="numero"
                            inputMode="decimal"
                            prefijo="S/"
                            value={linea.costo_unitario}
                            onChange={(evento) =>
                              cambiarCampoLinea(indice, 'costo_unitario', evento.target.value)
                            }
                          />
                        </div>
                        <span className="ml-auto text-sm font-semibold numero text-ink">
                          {formatearMoneda(
                            Decimal.desde(linea.cantidad).multiplica(linea.costo_unitario),
                          )}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              <div className="border-t border-linea px-4 py-3">
                <div className="flex items-center justify-between">
                  <span className="etiqueta">Costo total</span>
                  <span className="text-2xl font-bold numero text-ink">{formatearMoneda(total)}</span>
                </div>
                <p className="mt-2 text-xs text-muted">
                  Impacto: {impacto.length > 0 ? impacto.map((item) => item.texto).join(' · ') : '—'}
                </p>
                <Button
                  variante="primario"
                  tamano="lg"
                  anchoCompleto
                  className="mt-3"
                  disabled={lineas.length === 0}
                  onClick={() => setPaso(3)}
                >
                  Revisar y confirmar
                </Button>
              </div>
            </Card>
          </div>
        </div>
      ) : null}

      {/* --- Paso 3: revisar y confirmar --- */}
      {paso === 3 && proveedor ? (
        <Card titulo="Paso 3 · Revisar y confirmar" subtitulo="Comprueba los datos antes de registrar el ingreso">
          <CardBody className="flex flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <p className="etiqueta">Proveedor</p>
                <p className="text-sm font-semibold text-ink">{proveedor.razon_social}</p>
              </div>
              <div>
                <p className="etiqueta">Documento</p>
                <p className="text-sm text-ink">{documento || 'Sin documento'}</p>
              </div>
              <div>
                <p className="etiqueta">Fecha</p>
                <p className="text-sm numero text-ink">{formatearFecha(fecha)}</p>
              </div>
            </div>

            <Table descripcion="Líneas del ingreso en revisión">
              <TableHead>
                <TableHeader>Producto</TableHeader>
                <TableHeader>Presentación</TableHeader>
                <TableHeader className="text-right">Cantidad</TableHeader>
                <TableHeader className="text-right">Costo unitario</TableHeader>
                <TableHeader className="text-right">Subtotal</TableHeader>
              </TableHead>
              <TableBody>
                {lineas.map((linea) => (
                  <TableRow key={`${linea.producto_id}-${linea.presentacion_id}`}>
                    <TableCell>{linea.producto_nombre}</TableCell>
                    <TableCell>{linea.presentacion_nombre}</TableCell>
                    <TableCell numerica>
                      {formatearCantidad(linea.cantidad)}{' '}
                      <span className="text-xs text-muted">
                        = {formatearCantidad(
                          Decimal.desde(linea.cantidad).multiplica(linea.factor_base),
                        )}{' '}
                        {linea.unidad_base?.toLowerCase() ?? 'und'}
                      </span>
                    </TableCell>
                    <TableCell numerica>{formatearMoneda(linea.costo_unitario)}</TableCell>
                    <TableCell numerica>
                      {formatearMoneda(
                        Decimal.desde(linea.cantidad).multiplica(linea.costo_unitario),
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-linea pt-4">
              <div>
                <p className="etiqueta">Costo total del ingreso</p>
                <p className="text-2xl font-bold numero text-ink">{formatearMoneda(total)}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variante="secundario" onClick={() => setPaso(2)}>
                  Volver a productos
                </Button>
                <Button
                  variante="primario"
                  tamano="lg"
                  cargando={previsualizar.isPending}
                  textoCargando="Validando impacto…"
                  onClick={() => previsualizar.mutate()}
                >
                  Confirmar ingreso
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      ) : null}

      {/* --- Modal de impacto previo --- */}
      <Modal
        abierto={modalImpacto}
        titulo="Impacto del ingreso"
        descripcion="Así quedará el stock después de registrar este abastecimiento."
        ancho="lg"
        onCerrar={() => {
          setModalImpacto(false);
          setPrevia(null);
        }}
        pie={
          <>
            <Button
              variante="secundario"
              onClick={() => {
                setModalImpacto(false);
                setPrevia(null);
              }}
            >
              Volver
            </Button>
            <Button
              variante="primario"
              cargando={confirmar.isPending}
              textoCargando="Registrando ingreso…"
              onClick={() => confirmar.mutate()}
            >
              Registrar ingreso
            </Button>
          </>
        }
      >
        {previa ? (
          <div className="flex flex-col gap-4">
            {previa.alertas_stock_minimo > 0 ? (
              <Notice tono="aviso" titulo="Algunos productos quedarán por debajo del mínimo">
                {previa.alertas_stock_minimo} producto(s) seguirán bajo el stock mínimo después de
                este ingreso.
              </Notice>
            ) : (
              <Notice tono="exito" titulo="Sin alertas de stock mínimo">
                Ningún producto quedará por debajo de su mínimo configurado.
              </Notice>
            )}

            <div>
              <p className="etiqueta">Costo total</p>
              <p className="text-2xl font-bold numero text-ink">{formatearMoneda(previa.total)}</p>
            </div>

            <Table descripcion="Impacto del ingreso sobre las existencias">
              <TableHead>
                <TableHeader>Producto</TableHeader>
                <TableHeader className="text-right">Stock actual</TableHeader>
                <TableHeader className="text-right">Stock resultante</TableHeader>
              </TableHead>
              <TableBody>
                {previa.lineas.map((linea) => (
                  <TableRow key={`${linea.producto_id}-${linea.presentacion_id}`}>
                    <TableCell>
                      <span className="font-semibold">{linea.producto_nombre}</span>
                      <span className="ml-2 text-xs text-muted">{linea.presentacion_nombre}</span>
                    </TableCell>
                    <TableCell numerica>
                      {formatearEnUnidadLegible(linea.stock_actual_base, linea.unidad_base)}
                    </TableCell>
                    <TableCell numerica>
                      <span className="font-semibold text-brand">
                        {formatearEnUnidadLegible(linea.stock_resultante_base, linea.unidad_base)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
