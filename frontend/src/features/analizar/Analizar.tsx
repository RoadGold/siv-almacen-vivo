import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Button,
  Card,
  CardBody,
  Field,
  Input,
  Notice,
  useToast,
} from '@/design-system';
import { claves } from '@/shared/api/clavesConsulta';
import { reportesApi } from '@/shared/api/endpoints';
import { Decimal } from '@/shared/format/decimal';
import {
  formatearFecha,
  formatearMoneda,
  formatearNumero,
  formatearPorcentaje,
  haceDiasISO,
  hoyISO,
  inicioMesISO,
} from '@/shared/format/formato';
import { esSinPermisos, mensajeDeError } from '@/shared/hooks/errores';
import { guardarArchivo, nombreArchivoConPeriodo } from '@/shared/utils/descargas';
import {
  PanelConsulta,
  TablaAbastecimientosPorProveedor,
  TablaHistoricoCostos,
  TablaInventarioValorizado,
  TablaPorCategoria,
  TablaPorDia,
  TablaPorProducto,
  TablaPorUsuario,
} from './TablasReporte';

type VistaDetalle = 'producto' | 'categoria' | 'usuario';

const ATAJOS: { titulo: string; aplicar: () => { desde: string; hasta: string } }[] = [
  {
    titulo: 'Hoy',
    aplicar: () => ({ desde: hoyISO(), hasta: hoyISO() }),
  },
  {
    titulo: 'Este mes',
    aplicar: () => ({ desde: inicioMesISO(), hasta: hoyISO() }),
  },
  {
    titulo: 'Últimos 30 días',
    aplicar: () => ({ desde: haceDiasISO(29), hasta: hoyISO() }),
  },
];

const VISTAS: { id: VistaDetalle; titulo: string }[] = [
  { id: 'producto', titulo: 'Por producto' },
  { id: 'categoria', titulo: 'Por categoría' },
  { id: 'usuario', titulo: 'Por usuario' },
];

/**
 * Pantalla ANALIZAR: reportes de ventas, margen bruto estimado, abastecimientos,
 * histórico de costos e inventario valorizado (plan §5.7).
 */
export function Analizar() {
  const [desde, setDesde] = useState(inicioMesISO());
  const [hasta, setHasta] = useState(hoyISO());
  const [vista, setVista] = useState<VistaDetalle>('producto');
  const [descargando, setDescargando] = useState(false);
  const { notificar } = useToast();

  const periodo = useMemo(() => ({ desde, hasta }), [desde, hasta]);

  const ventas = useQuery({
    queryKey: claves.reportes.ventas(periodo),
    queryFn: () => reportesApi.ventas(periodo),
  });

  const margen = useQuery({
    queryKey: claves.reportes.margen(periodo),
    queryFn: () => reportesApi.margen(periodo),
  });

  const abastecimientos = useQuery({
    queryKey: claves.reportes.abastecimientos(periodo),
    queryFn: () => reportesApi.abastecimientos(periodo),
  });

  const costos = useQuery({
    queryKey: claves.reportes.costos({}),
    queryFn: () => reportesApi.costos({}),
  });

  const inventario = useQuery({
    queryKey: claves.reportes.inventario({}),
    queryFn: () => reportesApi.inventario(),
  });

  const valorInventario = useMemo(
    () =>
      (inventario.data ?? []).reduce(
        (total, fila) => total.suma(fila.valor_costo),
        Decimal.cero(),
      ),
    [inventario.data],
  );

  async function exportarCsv() {
    setDescargando(true);
    try {
      const archivo = await reportesApi.exportarVentasCsv(periodo);
      guardarArchivo(archivo, nombreArchivoConPeriodo('ventas', desde, hasta, 'csv'));
      notificar('Se descargó el detalle de ventas en CSV.', 'exito');
    } catch (error) {
      notificar(mensajeDeError(error), 'error');
    } finally {
      setDescargando(false);
    }
  }

  const permisoDenegado = esSinPermisos(ventas.error);

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="etiqueta">Analizar</p>
          <h1 className="mt-1 text-2xl font-bold text-ink">Reportes</h1>
          <p className="mt-1 text-sm text-muted">
            Ventas por periodo, margen bruto estimado, abastecimiento y valor del inventario.
          </p>
        </div>
        <Button
          variante="secundario"
          cargando={descargando}
          textoCargando="Generando CSV…"
          onClick={() => void exportarCsv()}
        >
          Exportar ventas (CSV)
        </Button>
      </header>

      {permisoDenegado ? (
        <Notice tono="error" titulo="No tienes permiso para consultar los reportes">
          Solicita a un administrador el permiso «reportes.ver».
        </Notice>
      ) : null}

      {/* --- Selector de periodo --- */}
      <Card titulo="Periodo" subtitulo="Las cifras se calculan en el servidor con agregaciones">
        <CardBody className="flex flex-col gap-4">
          <div className="flex flex-wrap items-end gap-3">
            <Field htmlFor="reporte-desde" etiqueta="Desde" className="w-[180px]">
              <Input
                id="reporte-desde"
                type="date"
                className="numero"
                value={desde}
                onChange={(evento) => setDesde(evento.target.value)}
              />
            </Field>
            <Field htmlFor="reporte-hasta" etiqueta="Hasta" className="w-[180px]">
              <Input
                id="reporte-hasta"
                type="date"
                className="numero"
                value={hasta}
                onChange={(evento) => setHasta(evento.target.value)}
              />
            </Field>
            <div className="flex flex-wrap gap-2">
              {ATAJOS.map((atajo) => (
                <Button
                  key={atajo.titulo}
                  variante="secundario"
                  tamano="sm"
                  onClick={() => {
                    const nuevo = atajo.aplicar();
                    setDesde(nuevo.desde);
                    setHasta(nuevo.hasta);
                  }}
                >
                  {atajo.titulo}
                </Button>
              ))}
            </div>
            <p className="ml-auto text-xs text-muted">
              Periodo mostrado: {formatearFecha(desde)} — {formatearFecha(hasta)}
            </p>
          </div>
        </CardBody>
      </Card>

      {/* --- Tarjetas de resumen --- */}
      <section aria-label="Resumen del periodo" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <TarjetaResumen
          titulo="Ventas del periodo"
          valor={formatearMoneda(ventas.data?.periodo.total ?? '0')}
          detalle={`${formatearNumero(ventas.data?.periodo.operaciones ?? 0, 0)} operaciones`}
          cargando={ventas.isLoading}
        />
        <TarjetaResumen
          titulo="Costo de mercadería vendida"
          valor={formatearMoneda(margen.data?.costo_mercaderia_vendida ?? '0')}
          detalle="Costo histórico de los productos vendidos"
          cargando={margen.isLoading}
        />
        <TarjetaResumen
          titulo="Margen bruto estimado"
          valor={formatearMoneda(margen.data?.margen_bruto_estimado ?? '0')}
          detalle={
            margen.data
              ? `${formatearPorcentaje(margen.data.margen_bruto_porcentaje)} sobre las ventas`
              : 'Ventas menos costo de mercadería vendida'
          }
          destacado
          cargando={margen.isLoading}
        />
        <TarjetaResumen
          titulo="Valor del inventario (costo)"
          valor={formatearMoneda(valorInventario)}
          detalle={`${formatearNumero(inventario.data?.length ?? 0, 0)} producto(s) con existencias`}
          cargando={inventario.isLoading}
        />
      </section>

      {margen.data?.nota ? (
        <Notice tono="info" titulo="Nota de lectura">
          {margen.data.nota}
        </Notice>
      ) : null}

      {/* --- Ventas por día --- */}
      <Card titulo="Ventas por día" subtitulo="Detalle diario del periodo seleccionado">
        <PanelConsulta
          cargando={ventas.isLoading}
          error={ventas.isError ? ventas.error : null}
          onReintentar={() => void ventas.refetch()}
        >
          {ventas.data ? <TablaPorDia reporte={ventas.data} /> : null}
        </PanelConsulta>
      </Card>

      {/* --- Detalle por producto / categoría / usuario --- */}
      <Card titulo="Desglose de ventas" subtitulo="Selecciona el eje del desglose">
        <div
          className="flex flex-wrap items-center gap-1 border-b border-linea px-4 py-2"
          role="tablist"
          aria-label="Desglose de ventas"
        >
          {VISTAS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={vista === item.id}
              onClick={() => setVista(item.id)}
              className={[
                'rounded-[6px] px-3 py-1.5 text-sm font-semibold transition-colors',
                vista === item.id ? 'bg-brand text-sobre-brand' : 'text-muted hover:text-brand',
              ].join(' ')}
            >
              {item.titulo}
            </button>
          ))}
        </div>
        <PanelConsulta
          cargando={ventas.isLoading}
          error={ventas.isError ? ventas.error : null}
          onReintentar={() => void ventas.refetch()}
        >
          {ventas.data ? (
            vista === 'producto' ? (
              <TablaPorProducto reporte={ventas.data} />
            ) : vista === 'categoria' ? (
              <TablaPorCategoria reporte={ventas.data} />
            ) : (
              <TablaPorUsuario reporte={ventas.data} />
            )
          ) : null}
        </PanelConsulta>
      </Card>

      {/* --- Abastecimientos por proveedor --- */}
      <Card titulo="Abastecimientos por proveedor" subtitulo="Ingresos de mercadería del periodo">
        <PanelConsulta
          cargando={abastecimientos.isLoading}
          error={abastecimientos.isError ? abastecimientos.error : null}
          onReintentar={() => void abastecimientos.refetch()}
        >
          <TablaAbastecimientosPorProveedor filas={abastecimientos.data ?? []} />
        </PanelConsulta>
      </Card>

      {/* --- Histórico de costos --- */}
      <Card
        titulo="Histórico de costos"
        subtitulo="Costo de compra registrado en cada abastecimiento confirmado"
      >
        <PanelConsulta
          cargando={costos.isLoading}
          error={costos.isError ? costos.error : null}
          onReintentar={() => void costos.refetch()}
        >
          <TablaHistoricoCostos filas={costos.data ?? []} />
        </PanelConsulta>
      </Card>

      {/* --- Inventario valorizado --- */}
      <Card
        titulo="Inventario valorizado"
        subtitulo="Cantidad y valor al costo promedio ponderado"
      >
        <PanelConsulta
          cargando={inventario.isLoading}
          error={inventario.isError ? inventario.error : null}
          onReintentar={() => void inventario.refetch()}
        >
          <TablaInventarioValorizado
            filas={inventario.data ?? []}
            total={valorInventario.aTexto()}
          />
        </PanelConsulta>
      </Card>
    </div>
  );
}

/** Tarjeta de indicador del periodo. */
function TarjetaResumen({
  titulo,
  valor,
  detalle,
  destacado = false,
  cargando = false,
}: {
  titulo: string;
  valor: string;
  detalle: string;
  destacado?: boolean;
  cargando?: boolean;
}) {
  return (
    <div
      className={[
        'rounded-tarjeta border px-4 py-4 shadow-panel',
        destacado ? 'border-brand bg-brand-tenue' : 'border-linea bg-surface',
      ].join(' ')}
    >
      <p className="etiqueta">{titulo}</p>
      <p className="mt-1 text-2xl font-bold numero text-ink">
        {cargando ? '—' : valor}
      </p>
      <p className="mt-1 text-xs text-muted">{detalle}</p>
    </div>
  );
}
