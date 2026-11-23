import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
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
import {
  catalogoApi,
  configuracionApi,
  inventarioApi,
  lotesApi,
  ventasApi,
} from '@/shared/api/endpoints';
import { Decimal } from '@/shared/format/decimal';
import { parsearEntradaNumerica } from '@/shared/format/entrada';
import {
  formatearCantidad,
  formatearEnUnidadLegible,
  formatearEquivalenciaSacos,
  formatearFecha,
  formatearMoneda,
} from '@/shared/format/formato';
import { useRetraso } from '@/shared/hooks/useRetraso';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { FilaResultado, type PeticionLote } from './ResultadoProducto';
import { buscarPorCodigoBarras, pareceCodigoBarras } from './buscarCodigoBarras';
import type { LineaCarrito, ResultadoBusqueda } from './tipos';
import { generarClaveIdempotencia, nuevoIdLinea, useCarritoVenta } from './useCarritoVenta';
import type {
  FormaPago,
  LoteResumen,
  PrevisualizacionVenta,
  Presentacion,
  Venta,
} from '@/shared/types/api';
import { SelectorLote, precioDeLote, type AsignacionLote } from './SelectorLote';

/**
 * Formas de pago que se muestran mientras el backend no responde.
 * La lista que manda el servidor es la que vale; esta solo evita que el
 * selector aparezca vacío en el primer instante.
 */
const FORMAS_PAGO_POR_DEFECTO: FormaPago[] = [
  { valor: 'efectivo', etiqueta: 'Efectivo' },
  { valor: 'tarjeta', etiqueta: 'Tarjeta' },
  { valor: 'voucher', etiqueta: 'Voucher' },
  { valor: 'yape', etiqueta: 'Yape / Plin' },
];

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
  const [peticionLote, setPeticionLote] = useState<PeticionLote | null>(null);

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

  // Las formas de pago las decide el backend: el cliente no las escribe a mano.
  const consultaFormasPago = useQuery({
    queryKey: ['configuracion', 'formas-pago'],
    queryFn: () => configuracionApi.formasPago(),
    staleTime: 60 * 60 * 1000,
  });

  const formasPago = consultaFormasPago.data ?? FORMAS_PAGO_POR_DEFECTO;

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
        await agregarConLotes(exacto, presentacion, '1');
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
        await agregarConLotes(
          {
            producto_id: coincidencia.producto.id,
            nombre: coincidencia.producto.nombre,
            codigo: coincidencia.producto.codigo,
            unidad_base: coincidencia.producto.unidad_base ?? null,
          },
          coincidencia.presentacion,
          '1',
        );
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

  /**
   * Agrega un producto al carrito resolviendo sus lotes:
   * - sin lotes o con uno solo → se agrega directo con el precio de ese lote;
   * - con varios → se abre el selector para que el cajero elija.
   */
  async function agregarConLotes(
    producto: {
      producto_id: number;
      nombre: string;
      codigo: string;
      unidad_base: string | null;
    },
    presentacion: Presentacion,
    cantidad: string,
  ) {
    const cantidadDecimal = Decimal.desde(cantidad);
    let lotes: LoteResumen[] = [];
    try {
      lotes = await lotesApi.listar(producto.producto_id, { solo_con_stock: true });
    } catch {
      lotes = [];
    }

    if (lotes.length > 1) {
      setPeticionLote({
        producto: {
          id: producto.producto_id,
          nombre: producto.nombre,
          codigo: producto.codigo,
        },
        presentacion,
        cantidad: cantidadDecimal.aTexto(),
        lotes,
      });
      return;
    }

    const lote = lotes[0] ?? null;
    const precio = lote
      ? precioDeLote(lote, presentacion.id)
      : Decimal.desde(presentacion.precio_venta);
    const total = precio.multiplica(cantidadDecimal).redondear(2);
    agregarLinea({
      producto_id: producto.producto_id,
      presentacion_id: presentacion.id,
      producto_nombre: producto.nombre,
      producto_codigo: producto.codigo,
      presentacion_nombre: presentacion.nombre,
      unidad_base: producto.unidad_base,
      factor_base: presentacion.factor_base,
      precio_original: precio.aTexto(),
      precio_total: total.aTexto(),
      precio_total_original: total.aTexto(),
      cantidad: cantidadDecimal.aTexto(),
      lote_id: lote?.id ?? null,
      lote_codigo: lote?.codigo_lote ?? null,
      lote_fecha_ingreso: lote?.fecha_ingreso ?? null,
    });
  }

  /** El cajero confirma el reparto por lotes. */
  function confirmarLotes(asignaciones: AsignacionLote[]) {
    const peticion = peticionLote;
    if (!peticion) return;
    const precioPorLote = new Map(
      peticion.lotes.map((lote) => [lote.id, precioDeLote(lote, peticion.presentacion.id)]),
    );
    for (const asignacion of asignaciones) {
      const precio = precioPorLote.get(asignacion.lote_id) ?? Decimal.cero();
      const cantidad = Decimal.desde(asignacion.cantidad);
      const total = precio.multiplica(cantidad).redondear(2);
      const lote = peticion.lotes.find((item) => item.id === asignacion.lote_id);
      agregarLinea({
        producto_id: peticion.producto.id,
        presentacion_id: peticion.presentacion.id,
        producto_nombre: peticion.producto.nombre,
        producto_codigo: peticion.producto.codigo,
        presentacion_nombre: peticion.presentacion.nombre,
        unidad_base: lote?.unidad_base ?? null,
        factor_base: peticion.presentacion.factor_base,
        precio_original: precio.aTexto(),
        precio_total: total.aTexto(),
        precio_total_original: total.aTexto(),
        cantidad: cantidad.aTexto(),
        lote_id: asignacion.lote_id,
        lote_codigo: asignacion.lote_codigo,
        lote_fecha_ingreso: lote?.fecha_ingreso ?? null,
      });
    }
    setPeticionLote(null);
    window.setTimeout(() => referenciaBuscador.current?.focus(), 0);
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
          cantidad: parsearEntradaNumerica(linea.cantidad),
          precio_total: parsearEntradaNumerica(linea.precio_total),
          motivo_precio: linea.motivo_precio ?? null,
          lote_id: linea.lote_id ?? null,
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
        monto_recibido:
          montoRecibido.trim() === '' ? null : parsearEntradaNumerica(montoRecibido) || null,
        lineas: carrito.lineas.map((linea) => ({
          producto_id: linea.producto_id,
          presentacion_id: linea.presentacion_id,
          cantidad: parsearEntradaNumerica(linea.cantidad),
          precio_total: parsearEntradaNumerica(linea.precio_total),
          motivo_precio: linea.motivo_precio ?? null,
          lote_id: linea.lote_id ?? null,
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
      cliente.invalidateQueries({ queryKey: ['reportes'] });
      cliente.invalidateQueries({ queryKey: ['lotes'] });

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

  /**
   * Cantidad ya pendiente en el carrito por cada lote (en unidad base).
   *
   * Se le pasa al selector de lote para que muestre el stock que **de verdad**
   * queda y no ofrezca más mercadería de la que hay.
   */
  const pendientesPorLote = useMemo(() => {
    const mapa: Record<number, string> = {};
    for (const linea of carrito.lineas) {
      if (linea.lote_id === null || linea.lote_id === undefined) continue;
      const base = Decimal.desde(linea.cantidad).multiplica(linea.factor_base);
      const actual = mapa[linea.lote_id];
      mapa[linea.lote_id] = Decimal.desde(actual ?? '0').suma(base).aTexto();
    }
    return mapa;
  }, [carrito.lineas]);

  const cintaLocal = useMemo(
    () =>
      carrito.lineas.map((linea) => {
        const cantNeg = Decimal.desde(linea.cantidad).multiplica(-1);
        const base = Decimal.desde(linea.cantidad).multiplica(linea.factor_base).multiplica(-1);
        const factor = Decimal.desde(linea.factor_base);
        const textoSacos =
          factor.comparar('1') > 0
            ? `${formatearEquivalenciaSacos(cantNeg, linea.presentacion_nombre)} (${formatearEnUnidadLegible(base, linea.unidad_base)})`
            : formatearEnUnidadLegible(base, linea.unidad_base);
        return {
          id: linea.id,
          texto: `${linea.producto_nombre} ${textoSacos}`,
        };
      }),
    [carrito.lineas],
  );

  const hayAlertas = (presentacionPrevia?.alertas.length ?? 0) > 0;

  /**
   * Revisa el carrito antes de confirmar: la cantidad debe ser un número mayor
   * que cero y el total un número no negativo.
   */
  const erroresCarrito = useMemo(() => {
    const errores: Record<string, { cantidad?: string; precio?: string }> = {};
    for (const linea of carrito.lineas) {
      const cantidad = parsearEntradaNumerica(linea.cantidad);
      const precio = parsearEntradaNumerica(linea.precio_total);
      if (cantidad === '') {
        errores[linea.id] = {
          ...(errores[linea.id] ?? {}),
          cantidad: 'La cantidad no tiene un valor numérico.',
        };
      } else if (Decimal.desde(cantidad).comparar(0) <= 0) {
        errores[linea.id] = {
          ...(errores[linea.id] ?? {}),
          cantidad: 'La cantidad debe ser mayor que cero.',
        };
      }
      if (precio === '') {
        errores[linea.id] = {
          ...(errores[linea.id] ?? {}),
          precio: 'El total no tiene un valor numérico.',
        };
      } else if (Decimal.desde(precio).comparar(0) < 0) {
        errores[linea.id] = {
          ...(errores[linea.id] ?? {}),
          precio: 'El total no puede ser negativo.',
        };
      }
    }
    return errores;
  }, [carrito.lineas]);

  const carritoInvalido = Object.keys(erroresCarrito).length > 0;

  const vuelto = useMemo(() => {
    if (formaPago !== 'efectivo') return null;
    if (!presentacionPrevia) return null;
    if (montoRecibido.trim() === '') return null;
    const recibido = Decimal.desde(parsearEntradaNumerica(montoRecibido) || '0');
    const total = Decimal.desde(presentacionPrevia.total);
    if (recibido.comparar(total) < 0) return null;
    return recibido.resta(total);
  }, [formaPago, montoRecibido, presentacionPrevia]);

  /**
   * Importe que quedaría sin cobrar cuando el efectivo no cubre el total.
   * La venta se permite, pero el sistema avisa: el backend registra la deuda
   * y la deja visible en el ticket.
   */
  const deuda = useMemo(() => {
    if (formaPago !== 'efectivo') return null;
    if (!presentacionPrevia) return null;
    if (montoRecibido.trim() === '') return null;
    const recibido = Decimal.desde(parsearEntradaNumerica(montoRecibido) || '0');
    const total = Decimal.desde(presentacionPrevia.total);
    if (recibido.comparar(total) >= 0) return null;
    return total.resta(recibido);
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
              <Field
                htmlFor="buscador-venta"
                etiqueta="Buscar producto"
                ejemplo="Arroz, código 0001 o código de barras…"
                compacto
              >
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
                  autoComplete="off"
                />
              </Field>
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
                <FilaResultado
                  key={resultado.producto_id}
                  resultado={resultado}
                  onAgregar={agregarLinea}
                  onSeleccionarLote={setPeticionLote}
                />
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
                        {linea.presentacion_nombre} ·{' '}
                        {formatearMoneda(linea.precio_original)} c/u (precio de lista)
                      </p>
                      {linea.lote_codigo ? (
                        <p className="mt-0.5 text-xs text-muted">
                          Lote <span className="numero font-semibold text-ink-suave">{linea.lote_codigo}</span>
                          {linea.lote_fecha_ingreso
                            ? ` · ingreso ${formatearFecha(linea.lote_fecha_ingreso)}`
                            : ''}
                        </p>
                      ) : null}
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
                    <div className="w-[104px]">
                      <Field
                        htmlFor={`linea-${linea.id}`}
                        etiqueta="Cantidad"
                        ejemplo="1"
                        compacto
                        error={erroresCarrito[linea.id]?.cantidad}
                      >
                        <Input
                          id={`linea-${linea.id}`}
                          className="numero"
                          inputMode="decimal"
                          invalido={Boolean(erroresCarrito[linea.id]?.cantidad)}
                          value={linea.cantidad}
                          onChange={(evento) =>
                            carrito.cambiarCantidad(linea.id, evento.target.value)
                          }
                        />
                      </Field>
                    </div>
                    <span className="text-xs text-muted">{linea.presentacion_nombre}</span>
                    <div className="ml-auto flex items-center gap-2">
                      <div className="w-[132px]">
                        <Field
                          htmlFor={`precio-${linea.id}`}
                          etiqueta="Total a cobrar"
                          ejemplo="8.00"
                          compacto
                          error={erroresCarrito[linea.id]?.precio}
                        >
                          <Input
                            id={`precio-${linea.id}`}
                            className="numero"
                            inputMode="decimal"
                            invalido={Boolean(erroresCarrito[linea.id]?.precio)}
                            value={linea.precio_total}
                            onChange={(evento) =>
                              carrito.cambiarPrecio(linea.id, evento.target.value)
                            }
                          />
                        </Field>
                      </div>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {formatearCantidad(linea.cantidad)} x{' '}
                    {formatearMoneda(
                      Decimal.desde(linea.precio_total)
                        .divide(linea.cantidad, 4)
                        .redondear(2)
                        .aTexto(),
                    )}{' '}
                    = <span className="font-semibold text-ink">{formatearMoneda(linea.precio_total)}</span>
                  </p>
                  {Decimal.desde(linea.precio_total).comparar(linea.precio_total_original) !== 0 ? (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Badge tono="aviso">Total modificado</Badge>
                      <span className="text-xs text-muted">
                        de {formatearMoneda(linea.precio_total_original)}
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
            {carritoInvalido ? (
              <Notice
                tono="error"
                titulo="Revisa el carrito antes de confirmar"
                className="mb-3"
              >
                <ul className="list-disc pl-5">
                  {Object.entries(erroresCarrito).map(([id, error]) => (
                    <li key={id}>
                      {carrito.lineas.find((linea) => linea.id === id)?.producto_nombre}:{' '}
                      {error.cantidad ?? error.precio}
                    </li>
                  ))}
                </ul>
              </Notice>
            ) : null}
            <Button
              variante="primario"
              tamano="lg"
              anchoCompleto
              className="mt-3"
              disabled={carrito.vacia || carritoInvalido}
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
                  <Field
                    htmlFor="forma-pago"
                    etiqueta="Forma de pago"
                    compacto
                  >
                    <select
                      id="forma-pago"
                      value={formaPago}
                      onChange={(evento) => setFormaPago(evento.target.value)}
                      className="w-full rounded-[6px] border border-linea bg-surface px-2 py-1.5 text-sm text-ink"
                    >
                      {formasPago.map((forma) => (
                        <option key={forma.valor} value={forma.valor}>
                          {forma.etiqueta}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
                {formaPago === 'efectivo' ? (
                  <div className="w-[150px]">
                    <Field
                      htmlFor="monto-recibido"
                      etiqueta="Recibido"
                      compacto
                      error={
                        montoRecibido.trim() !== '' &&
                        parsearEntradaNumerica(montoRecibido) === ''
                          ? 'No es un número válido.'
                          : undefined
                      }
                    >
                      <Input
                        id="monto-recibido"
                        className="numero"
                        inputMode="decimal"
                        invalido={
                          montoRecibido.trim() !== '' &&
                          parsearEntradaNumerica(montoRecibido) === ''
                        }
                        value={montoRecibido}
                        onChange={(evento) => setMontoRecibido(evento.target.value)}
                        placeholder={presentacionPrevia.total}
                      />
                    </Field>
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
                {deuda ? (
                  <div>
                    <p className="etiqueta">Queda por cobrar</p>
                    <p className="text-lg font-bold numero text-danger">
                      {formatearMoneda(deuda.aTexto())}
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

              {deuda ? (
                <Notice
                  tono="aviso"
                  titulo="El efectivo no cubre el total"
                  className="mt-3"
                >
                  Faltan {formatearMoneda(deuda.aTexto())}. La venta se registra igual y el
                  importe queda anotado como deuda en el ticket y en la venta.
                </Notice>
              ) : null}
            </fieldset>

            <Table descripcion="Detalle del impacto de la venta">
              <TableHead>
                <TableHeader>Producto</TableHeader>
                <TableHeader>Presentación</TableHeader>
                <TableHeader className="text-right">Cantidad</TableHeader>
                <TableHeader className="text-right">Total</TableHeader>
                <TableHeader className="text-right">Stock actual</TableHeader>
                <TableHeader className="text-right">Saldo final</TableHeader>
              </TableHead>
              <TableBody>
                {presentacionPrevia.lineas.map((linea) => (
                  <TableRow
                    key={`${linea.producto_id}-${linea.presentacion_id}-${linea.lote_id ?? 'sin-lote'}`}
                  >
                    <TableCell>
                      {linea.producto_nombre}
                      {linea.lote_codigo ? (
                        <span className="ml-1">
                          <Badge tono="neutro">{linea.lote_codigo}</Badge>
                        </span>
                      ) : null}
                    </TableCell>
                    <TableCell>{linea.presentacion_nombre}</TableCell>
                    <TableCell numerica>
                      {formatearCantidad(linea.cantidad)} {linea.presentacion_nombre}
                    </TableCell>
                    <TableCell numerica>
                      {formatearMoneda(linea.precio_total)}
                      {linea.precio_total_original !== linea.precio_total ? (
                        <span className="ml-1 text-xs text-muted line-through">
                          {formatearMoneda(linea.precio_total_original)}
                        </span>
                      ) : null}
                      {linea.descuento_porcentaje !== '0' ? (
                        <span className="ml-1 text-xs text-warning">
                          −{formatearCantidad(linea.descuento_porcentaje)}%
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

      {/* --- Selector de lote (producto con varios lotes) --- */}
      <SelectorLote
        abierto={peticionLote !== null}
        onCerrar={() => setPeticionLote(null)}
        producto={peticionLote?.producto ?? null}
        presentacion={peticionLote?.presentacion ?? null}
        cantidad={peticionLote?.cantidad ?? '1'}
        lotes={peticionLote?.lotes ?? []}
        pendientesPorLote={pendientesPorLote}
        onConfirmar={confirmarLotes}
      />

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
