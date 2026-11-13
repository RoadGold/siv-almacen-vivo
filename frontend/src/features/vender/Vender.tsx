import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  EmptyState,
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
import { catalogoApi, inventarioApi, ventasApi } from '@/shared/api/endpoints';
import { Decimal } from '@/shared/format/decimal';
import {
  formatearCantidad,
  formatearEnUnidadLegible,
  formatearFecha,
  formatearMoneda,
} from '@/shared/format/formato';
import { useRetraso } from '@/shared/hooks/useRetraso';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { FilaResultado } from './ResultadoProducto';
import { buscarPorCodigoBarras, pareceCodigoBarras } from './buscarCodigoBarras';
import type { LineaCarrito, ResultadoBusqueda } from './tipos';
import { generarClaveIdempotencia, nuevoIdLinea, useCarritoVenta } from './useCarritoVenta';
import type { PrevisualizacionVenta, Venta } from '@/shared/types/api';

/** Pantalla VENDER: dos paneles (buscador y carrito) con cinta de impacto. */
export function Vender() {
  const [busqueda, setBusqueda] = useState('');
  const busquedaRetrasada = useRetraso(busqueda, 250);
  const [codigoEnviado, setCodigoEnviado] = useState(false);

  const referenciaBuscador = useRef<HTMLInputElement>(null);
  const cliente = useQueryClient();
  const { notificar } = useToast();
  const carrito = useCarritoVenta();

  const [presentacionPrevia, setPresentacionPrevia] = useState<PrevisualizacionVenta | null>(null);
  const [modalImpacto, setModalImpacto] = useState(false);
  const [modalDetalle, setModalDetalle] = useState(false);
  const [ventaRegistrada, setVentaRegistrada] = useState<Venta | null>(null);
  const [formaPago, setFormaPago] = useState('efectivo');
  const [montoRecibido, setMontoRecibido] = useState('');
  const [imprimirTicket, setImprimirTicket] = useState(true);
  const [estadoImpresion, setEstadoImpresion] = useState<{
    ok: boolean;
    mensaje: string;
  } | null>(null);

  // --- Atajos de teclado: F3 enfoca el buscador, Esc limpia la búsqueda ---
  useEffect(() => {
    function manejarTecla(evento: KeyboardEvent) {
      if (evento.key === 'F3') {
        evento.preventDefault();
        referenciaBuscador.current?.focus();
        referenciaBuscador.current?.select();
        return;
      }
      if (evento.key === 'Escape' && !modalImpacto && !modalDetalle) {
        setBusqueda('');
        referenciaBuscador.current?.focus();
      }
    }
    window.addEventListener('keydown', manejarTecla);
    return () => window.removeEventListener('keydown', manejarTecla);
  }, [modalImpacto, modalDetalle]);

  const consultaProductos = useQuery({
    queryKey: claves.productos.listado({ busqueda: busquedaRetrasada, tamano: 25 }),
    queryFn: () =>
      catalogoApi.listarProductos({
        q: busquedaRetrasada || undefined,
        pagina: 1,
        tamano: 25,
      }),
    enabled: !codigoEnviado,
  });

  const consultaExistencias = useQuery({
    queryKey: claves.existencias({ busqueda: busquedaRetrasada, tamano: 25 }),
    queryFn: () =>
      inventarioApi.existencias({
        q: busquedaRetrasada || undefined,
        pagina: 1,
        tamano: 25,
      }),
    enabled: !codigoEnviado,
  });

  const resultados = useMemo<ResultadoBusqueda[]>(() => {
    const productos = consultaProductos.data?.items ?? [];
    const existencias = new Map(
      (consultaExistencias.data?.items ?? []).map((item) => [item.producto_id, item]),
    );

    return productos.map((producto) => {
      const existencia = existencias.get(producto.id);
      return {
        producto_id: producto.id,
        codigo: producto.codigo,
        nombre: producto.nombre,
        unidad_base: producto.unidad_base ?? null,
        stock_base: existencia?.cantidad_base ?? '0',
        estado: existencia?.estado ?? 'agotado',
        presentacion_principal: existencia?.presentacion_principal ?? null,
        cantidad_presentacion: existencia?.cantidad_presentacion ?? null,
        presentaciones: producto.presentaciones,
      };
    });
  }, [consultaProductos.data, consultaExistencias.data]);

  /** Envío con Enter: coincidencia exacta por código o por código de barras. */
  async function enviarBusqueda() {
    const texto = busqueda.trim();
    if (!texto) return;

    // 1. Coincidencia por código interno exacto: se añade directamente.
    const exacto = resultados.find((item) => item.codigo.toLowerCase() === texto.toLowerCase());
    if (exacto) {
      const presentacion = exacto.presentaciones.find((item) => item.activo && item.es_venta);
      if (presentacion) {
        agregarLinea({
          producto_id: exacto.producto_id,
          presentacion_id: presentacion.id,
          producto_nombre: exacto.nombre,
          producto_codigo: exacto.codigo,
          presentacion_nombre: presentacion.nombre,
          unidad_base: exacto.unidad_base,
          factor_base: presentacion.factor_base,
          precio_unitario: presentacion.precio_venta,
          precio_original: presentacion.precio_venta,
          cantidad: '1',
        });
        setBusqueda('');
        return;
      }
    }

    // 2. Lectura de código de barras: coincidencia exacta en el catálogo.
    if (!pareceCodigoBarras(texto)) return;

    setCodigoEnviado(true);
    try {
      const coincidencia = await buscarPorCodigoBarras(texto);
      if (coincidencia) {
        agregarLinea({
          producto_id: coincidencia.producto.id,
          presentacion_id: coincidencia.presentacion.id,
          producto_nombre: coincidencia.producto.nombre,
          producto_codigo: coincidencia.producto.codigo,
          presentacion_nombre: coincidencia.presentacion.nombre,
          unidad_base: coincidencia.producto.unidad_base ?? null,
          factor_base: coincidencia.presentacion.factor_base,
          precio_unitario: coincidencia.presentacion.precio_venta,
          precio_original: coincidencia.presentacion.precio_venta,
          cantidad: '1',
        });
        setBusqueda('');
        notificar(`Añadido: ${coincidencia.producto.nombre}`, 'exito');
      } else {
        notificar(`No existe ninguna presentación con el código ${texto}.`, 'error');
      }
    } catch {
      notificar('No se pudo consultar el código de barras.', 'error');
    } finally {
      setCodigoEnviado(false);
    }
  }

  function agregarLinea(linea: Omit<LineaCarrito, 'id'>) {
    carrito.agregar({ ...linea, id: nuevoIdLinea() });
    // El foco vuelve al buscador para continuar escaneando.
    window.setTimeout(() => referenciaBuscador.current?.focus(), 0);
  }

  // --- Previsualización y confirmación ---
  const previsualizar = useMutation({
    mutationFn: () =>
      ventasApi.previsualizar({
        lineas: carrito.lineas.map((linea) => ({
          producto_id: linea.producto_id,
          presentacion_id: linea.presentacion_id,
          cantidad: linea.cantidad,
          precio_unitario: linea.precio_unitario,
          motivo_precio: linea.motivo_precio ?? null,
        })),
      }),
    onSuccess: (respuesta) => {
      setPresentacionPrevia(respuesta);
      setModalImpacto(true);
    },
    onError: (error) => {
      notificar(mensajeDeError(error), 'error');
    },
  });

  const [claveIdempotencia, setClaveIdempotencia] = useState(() => generarClaveIdempotencia());

  const confirmar = useMutation({
    mutationFn: (clave: string) =>
      ventasApi.confirmar({
        idempotency_key: clave,
        forma_pago: formaPago,
        monto_recibido: montoRecibido.trim() === '' ? null : montoRecibido,
        lineas: carrito.lineas.map((linea) => ({
          producto_id: linea.producto_id,
          presentacion_id: linea.presentacion_id,
          cantidad: linea.cantidad,
          precio_unitario: linea.precio_unitario,
          motivo_precio: linea.motivo_precio ?? null,
        })),
      }),
    onSuccess: (venta) => {
      setVentaRegistrada(venta);
      setModalImpacto(false);
      setPresentacionPrevia(null);
      carrito.limpiar();
      setClaveIdempotencia(generarClaveIdempotencia());
      setMontoRecibido('');
      registrarOperacion(`Venta ${venta.numero}`);
      notificar(`Venta ${venta.numero} registrada correctamente.`, 'exito');
      cliente.invalidateQueries({ queryKey: ['dashboard'] });
      cliente.invalidateQueries({ queryKey: ['inventario'] });
      cliente.invalidateQueries({ queryKey: ['ventas'] });

      // Impresión del ticket: la venta ya está registrada; si el papel falla,
      // el ticket queda pendiente y se puede reintentar.
      if (imprimirTicket) {
        ventasApi
          .imprimir(venta.id)
          .then((resultado) => {
            setEstadoImpresion({ ok: resultado.ok, mensaje: resultado.mensaje });
          })
          .catch((error) => {
            setEstadoImpresion({
              ok: false,
              mensaje: `La venta se registró, pero el ticket no salió: ${mensajeDeError(error)}`,
            });
          });
      } else {
        setEstadoImpresion(null);
      }
    },
    onError: (error) => {
      notificar(mensajeDeError(error), 'error');
    },
  });

  const cintaLocal = useMemo(
    () =>
      carrito.lineas.map((linea) => {
        const base = Decimal.desde(linea.cantidad).multiplica(linea.factor_base).multiplica(-1);
        return {
          id: linea.id,
          texto: `${linea.producto_nombre} ${formatearEnUnidadLegible(base, linea.unidad_base)}`,
        };
      }),
    [carrito.lineas],
  );

  const hayAlertas = (presentacionPrevia?.alertas.length ?? 0) > 0;

  const vuelto = useMemo(() => {
    if (formaPago !== 'efectivo') return null;
    if (!presentacionPrevia) return null;
    if (montoRecibido.trim() === '') return null;
    const recibido = Decimal.desde(montoRecibido);
    const total = Decimal.desde(presentacionPrevia.total);
    if (recibido.comparar(total) < 0) return null;
    return recibido.resta(total);
  }, [formaPago, montoRecibido, presentacionPrevia]);

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="etiqueta">Estación · Vender</p>
          <h1 className="mt-1 text-2xl font-bold text-ink">Venta nueva</h1>
          <p className="mt-1 text-sm text-muted">
            {ventaRegistrada
              ? `Venta ${ventaRegistrada.numero} registrada. Puedes iniciar otra venta.`
              : 'Busca por nombre o código, escanea el código de barras y revisa el impacto antes de confirmar.'}
          </p>
        </div>
        {ventaRegistrada ? (
          <div className="flex flex-wrap gap-2">
            <Button variante="acento" onClick={() => setVentaRegistrada(null)}>
              Nueva venta
            </Button>
            <Button variante="secundario" onClick={() => setModalDetalle(true)}>
              Ver detalle
            </Button>
          </div>
        ) : null}
      </header>

      {estadoImpresion ? (
        <Notice
          tono={estadoImpresion.ok ? 'exito' : 'error'}
          titulo={
            estadoImpresion.ok
              ? 'Ticket impreso'
              : 'Venta registrada, pero el ticket no salió'
          }
          acciones={
            estadoImpresion.ok ? undefined : (
              <Button
                variante="secundario"
                tamano="sm"
                onClick={() => {
                  if (!ventaRegistrada) return;
                  ventasApi
                    .imprimir(ventaRegistrada.id)
                    .then((resultado) =>
                      setEstadoImpresion({ ok: resultado.ok, mensaje: resultado.mensaje }),
                    )
                    .catch((error) =>
                      setEstadoImpresion({
                        ok: false,
                        mensaje: mensajeDeError(error),
                      }),
                    );
                }}
              >
                Reintentar impresión
              </Button>
            )
          }
        >
          {estadoImpresion.mensaje} Puedes reimprimir el ticket desde el historial de ventas.
        </Notice>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        {/* --- Panel izquierdo: buscador y resultados --- */}
        <Card
          titulo="Buscar producto"
          subtitulo="Por nombre, código interno o código de barras"
          className="min-h-[420px]"
        >
          <div className="flex flex-wrap items-end gap-2 px-4 py-3">
            <div className="min-w-[260px] flex-1">
              <label htmlFor="buscador-venta" className="sr-only">
                Buscar producto para la venta
              </label>
              <Input
                id="buscador-venta"
                ref={referenciaBuscador}
                value={busqueda}
                onChange={(evento) => setBusqueda(evento.target.value)}
                onKeyDown={(evento) => {
                  if (evento.key === 'Enter') {
                    evento.preventDefault();
                    void enviarBusqueda();
                  }
                }}
                placeholder="Arroz, código 0001 o código de barras…"
                autoComplete="off"
              />
            </div>
            <Button
              variante="secundario"
              onClick={() => {
                setBusqueda('');
                referenciaBuscador.current?.focus();
              }}
            >
              Limpiar
            </Button>
          </div>

          <p className="px-4 pb-2 text-xs text-muted">
            <kbd className="rounded border border-linea-fuerte px-1">F3</kbd> enfoca el buscador ·{' '}
            <kbd className="rounded border border-linea-fuerte px-1">Esc</kbd> limpia la búsqueda
          </p>

          {consultaProductos.isError ? (
            <div className="px-4 pb-4">
              <Notice tono="error" titulo="No se pudo buscar en el catálogo">
                {esSinPermisos(consultaProductos.error)
                  ? 'No tienes permiso para consultar el catálogo.'
                  : mensajeDeError(consultaProductos.error)}
              </Notice>
            </div>
          ) : consultaProductos.isLoading ? (
            <LoadingBlock etiqueta="Buscando productos…" />
          ) : resultados.length === 0 ? (
            <EmptyState
              titulo="Sin resultados"
              descripcion={
                busqueda
                  ? 'Ningún producto coincide con la búsqueda.'
                  : 'Escribe el nombre de un producto o escanea su código de barras para empezar.'
              }
            />
          ) : (
            <div className="border-t border-linea">
              {resultados.map((resultado) => (
                <FilaResultado key={resultado.producto_id} resultado={resultado} onAgregar={agregarLinea} />
              ))}
            </div>
          )}
        </Card>

        {/* --- Panel derecho: carrito --- */}
        <Card
          titulo="Tu venta"
          subtitulo={carrito.vacia ? 'Sin líneas por ahora' : `${carrito.lineas.length} línea(s)`}
          className="flex flex-col"
        >
          {carrito.vacia ? (
            <EmptyState
              titulo="El carrito está vacío"
              descripcion="Busca un producto y pulsa «Añadir» para incorporar una línea."
            />
          ) : (
            <ul className="divide-y divide-linea">
              {carrito.lineas.map((linea) => (
                <li key={linea.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink">{linea.producto_nombre}</p>
                      <p className="text-xs text-muted">
                        {linea.presentacion_nombre} · {formatearMoneda(linea.precio_unitario)} c/u
                      </p>
                    </div>
                    <Button
                      variante="fantasma"
                      tamano="sm"
                      onClick={() => carrito.quitar(linea.id)}
                      aria-label={`Quitar ${linea.producto_nombre} del carrito`}
                    >
                      Quitar
                    </Button>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <div className="w-[92px]">
                      <label htmlFor={`linea-${linea.id}`} className="sr-only">
                        Cantidad de {linea.producto_nombre}
                      </label>
                      <Input
                        id={`linea-${linea.id}`}
                        className="numero"
                        inputMode="decimal"
                        value={linea.cantidad}
                        onChange={(evento) => carrito.cambiarCantidad(linea.id, evento.target.value)}
                      />
                    </div>
                    <span className="text-xs text-muted">{linea.presentacion_nombre}</span>
                    <div className="ml-auto flex items-center gap-2">
                      <div className="w-[104px]">
                        <label htmlFor={`precio-${linea.id}`} className="sr-only">
                          Precio unitario de {linea.producto_nombre}
                        </label>
                        <Input
                          id={`precio-${linea.id}`}
                          className="numero"
                          inputMode="decimal"
                          value={linea.precio_unitario}
                          onChange={(evento) =>
                            carrito.cambiarPrecio(linea.id, evento.target.value)
                          }
                        />
                      </div>
                      <span className="text-sm font-semibold numero text-ink">
                        {formatearMoneda(
                          Decimal.desde(linea.cantidad).multiplica(linea.precio_unitario),
                        )}
                      </span>
                    </div>
                  </div>
                  {Decimal.desde(linea.precio_unitario).comparar(linea.precio_original) !== 0 ? (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Badge tono="aviso">Precio modificado</Badge>
                      <span className="text-xs text-muted">
                        de {formatearMoneda(linea.precio_original)} c/u
                      </span>
                      <select
                        aria-label={`Motivo del cambio de precio de ${linea.producto_nombre}`}
                        value={linea.motivo_precio ?? ''}
                        onChange={(evento) =>
                          carrito.cambiarMotivo(linea.id, evento.target.value)
                        }
                        className="rounded-[6px] border border-linea bg-surface px-2 py-1 text-xs text-ink"
                      >
                        <option value="">Motivo (opcional)</option>
                        <option value="Promoción">Promoción</option>
                        <option value="Cliente especial">Cliente especial</option>
                        <option value="Error de captura">Error de captura</option>
                        <option value="Precio de lista">Precio de lista</option>
                        <option value="Descuento comercial">Descuento comercial</option>
                      </select>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}

          <div className="mt-auto border-t border-linea px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="etiqueta">Total</span>
              <span className="text-2xl font-bold numero text-ink">
                {formatearMoneda(carrito.total)}
              </span>
            </div>
            <Button
              variante="primario"
              tamano="lg"
              anchoCompleto
              className="mt-3"
              disabled={carrito.vacia}
              cargando={previsualizar.isPending}
              textoCargando="Calculando impacto…"
              onClick={() => previsualizar.mutate()}
            >
              Confirmar venta
            </Button>
          </div>
        </Card>
      </div>

      {/* --- Cinta de impacto --- */}
      <div className="cinta-impacto" aria-live="polite">
        {cintaLocal.length === 0 ? (
          <p className="text-muted">
            <span className="etiqueta mr-2">Impacto</span>
            Añade productos para ver qué stock TLRá a cambiar.
          </p>
        ) : (
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="etiqueta">Impacto</span>
            <span className="text-ink">
              {cintaLocal.map((item, indice) => (
                <span key={item.id}>
                  {indice > 0 ? ' · ' : ''}
                  {item.texto}
                </span>
              ))}
            </span>
            <span className="text-muted">· el saldo real se valida en el servidor.</span>
          </p>
        )}
      </div>

      {/* --- Modal de impacto previo a la confirmación --- */}
      <Modal
        abierto={modalImpacto}
        titulo="Impacto de la venta"
        descripcion="Estos son los saldos que el servidor validará al registrar la venta."
        ancho="lg"
        onCerrar={() => {
          setModalImpacto(false);
          setPresentacionPrevia(null);
        }}
        pie={
          <>
            <Button
              variante="secundario"
              onClick={() => {
                setModalImpacto(false);
                setPresentacionPrevia(null);
              }}
            >
              Volver a la venta
            </Button>
            <Button
              variante="primario"
              disabled={hayAlertas || !presentacionPrevia || presentacionPrevia.lineas.length === 0}
              cargando={confirmar.isPending}
              textoCargando="Registrando venta…"
              onClick={() => confirmar.mutate(claveIdempotencia)}
            >
              Registrar venta
            </Button>
          </>
        }
      >
        {presentacionPrevia ? (
          <div className="flex flex-col gap-4">
            {hayAlertas ? (
              <Notice tono="aviso" titulo="El servidor detectó un problema de stock">
                <ul className="list-disc pl-5">
                  {presentacionPrevia.alertas.map((alerta) => (
                    <li key={alerta}>{alerta}</li>
                  ))}
                </ul>
                <p className="mt-2">Ajusta las cantidades antes de registrar la venta.</p>
              </Notice>
            ) : (
              <Notice tono="exito" titulo="Stock validado">
                Hay existencias suficientes para todas las líneas de la venta.
              </Notice>
            )}

            <div className="flex flex-wrap gap-6">
              <div>
                <p className="etiqueta">Total a cobrar</p>
                <p className="text-2xl font-bold numero text-ink">
                  {formatearMoneda(presentacionPrevia.total)}
                </p>
              </div>
              <div>
                <p className="etiqueta">Costo estimado</p>
                <p className="text-2xl font-bold numero text-ink">
                  {formatearMoneda(presentacionPrevia.costo_estimado)}
                </p>
              </div>
            </div>

            {/* --- Cobro --- */}
            <fieldset className="rounded-[6px] border border-linea px-4 py-3">
              <legend className="px-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted">
                Cobro
              </legend>
              <div className="flex flex-wrap items-end gap-3">
                <div className="w-[170px]">
                  <label
                    htmlFor="forma-pago"
                    className="mb-1 block text-xs font-semibold text-ink"
                  >
                    Forma de pago
                  </label>
                  <select
                    id="forma-pago"
                    value={formaPago}
                    onChange={(evento) => setFormaPago(evento.target.value)}
                    className="w-full rounded-[6px] border border-linea bg-surface px-2 py-1.5 text-sm text-ink"
                  >
                    <option value="efectivo">Efectivo</option>
                    <option value="tarjeta">Tarjeta</option>
                    <option value="voucher">Voucher</option>
                    <option value="yape">Yape / Plin</option>
                  </select>
                </div>
                {formaPago === 'efectivo' ? (
                  <div className="w-[150px]">
                    <label
                      htmlFor="monto-recibido"
                      className="mb-1 block text-xs font-semibold text-ink"
                    >
                      Recibido
                    </label>
                    <Input
                      id="monto-recibido"
                      className="numero"
                      inputMode="decimal"
                      value={montoRecibido}
                      onChange={(evento) => setMontoRecibido(evento.target.value)}
                      placeholder={presentacionPrevia.total}
                    />
                  </div>
                ) : null}
                {vuelto ? (
                  <div>
                    <p className="etiqueta">Vuelto</p>
                    <p className="text-lg font-bold numero text-ink">
                      {formatearMoneda(vuelto.aTexto())}
                    </p>
                  </div>
                ) : null}
                <label className="flex items-center gap-2 pb-1 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={imprimirTicket}
                    onChange={(evento) => setImprimirTicket(evento.target.checked)}
                  />
                  Imprimir ticket
                </label>
              </div>
            </fieldset>

            <Table descripcion="Detalle del impacto de la venta">
              <TableHead>
                <TableHeader>Producto</TableHeader>
                <TableHeader>Presentación</TableHeader>
                <TableHeader className="text-right">Cantidad</TableHeader>
                <TableHeader className="text-right">Precio</TableHeader>
                <TableHeader className="text-right">Stock actual</TableHeader>
                <TableHeader className="text-right">Saldo final</TableHeader>
              </TableHead>
              <TableBody>
                {presentacionPrevia.lineas.map((linea) => (
                  <TableRow key={`${linea.producto_id}-${linea.presentacion_id}`}>
                    <TableCell>{linea.producto_nombre}</TableCell>
                    <TableCell>{linea.presentacion_nombre}</TableCell>
                    <TableCell numerica>
                      {formatearCantidad(linea.cantidad)} {linea.presentacion_nombre}
                    </TableCell>
                    <TableCell numerica>
                      {formatearMoneda(linea.precio_unitario)}
                      {linea.precio_original !== linea.precio_unitario ? (
                        <span className="ml-1 text-xs text-muted line-through">
                          {formatearMoneda(linea.precio_original)}
                        </span>
                      ) : null}
                    </TableCell>
                    <TableCell numerica>
                      {formatearEnUnidadLegible(linea.stock_actual_base, linea.unidad_base)}
                    </TableCell>
                    <TableCell numerica>
                      <span
                        className={
                          linea.alerta ? 'font-semibold text-danger' : 'text-ink'
                        }
                      >
                        {formatearEnUnidadLegible(linea.stock_resultante_base, linea.unidad_base)}
                      </span>
                      {linea.alerta ? (
                        <Badge tono="peligro" className="ml-2">
                          {linea.alerta === 'precio_fuera_de_limite'
                            ? 'Precio fuera de límite'
                            : 'Sin stock'}
                        </Badge>
                      ) : null}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </Modal>

      {/* --- Detalle de la venta registrada --- */}
      <Modal
        abierto={modalDetalle}
        titulo={ventaRegistrada ? `Venta ${ventaRegistrada.numero}` : 'Detalle de la venta'}
        descripcion={
          ventaRegistrada
            ? `${formatearFecha(ventaRegistrada.fecha)} · ${ventaRegistrada.usuario ?? 'sistema'}`
            : undefined
        }
        ancho="lg"
        onCerrar={() => setModalDetalle(false)}
        pie={
          <Button variante="secundario" onClick={() => setModalDetalle(false)}>
            Cerrar
          </Button>
        }
      >
        {ventaRegistrada ? (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-6">
              <div>
                <p className="etiqueta">Total</p>
                <p className="text-2xl font-bold numero text-ink">
                  {formatearMoneda(ventaRegistrada.total)}
                </p>
              </div>
              <div>
                <p className="etiqueta">Costo</p>
                <p className="text-2xl font-bold numero text-ink">
                  {formatearMoneda(ventaRegistrada.costo_total)}
                </p>
              </div>
            </div>
            <Table descripcion="Detalle de la venta registrada">
              <TableHead>
                <TableHeader>Producto</TableHeader>
                <TableHeader>Presentación</TableHeader>
                <TableHeader className="text-right">Cantidad</TableHeader>
                <TableHeader className="text-right">Precio</TableHeader>
                <TableHeader className="text-right">Subtotal</TableHeader>
              </TableHead>
              <TableBody>
                {ventaRegistrada.detalles.map((detalle) => (
                  <TableRow key={detalle.id}>
                    <TableCell>{detalle.producto_nombre}</TableCell>
                    <TableCell>{detalle.presentacion_nombre}</TableCell>
                    <TableCell numerica>{formatearCantidad(detalle.cantidad)}</TableCell>
                    <TableCell numerica>{formatearMoneda(detalle.precio_unitario)}</TableCell>
                    <TableCell numerica>{formatearMoneda(detalle.subtotal)}</TableCell>
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
