import type { ReactNode } from 'react';
import {
  EmptyState,
  LoadingBlock,
  Notice,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHead,
  TableRow,
} from '@/design-system';
import {
  formatearCantidad,
  formatearFecha,
  formatearMoneda,
  formatearNumero,
} from '@/shared/format/formato';
import type {
  AbastecimientosPorProveedor,
  CostoHistoricoReporte,
  InventarioValorizado,
  ReporteVentas,
} from '@/shared/types/api';

/** Tabla de ventas agrupadas por día. */
export function TablaPorDia({ reporte }: { reporte: ReporteVentas }) {
  if (reporte.periodo.por_dia.length === 0) {
    return (
      <EmptyState
        titulo="Sin ventas en el periodo"
        descripcion="Prueba con otras fechas o consulta el mes en curso."
      />
    );
  }

  return (
    <Table descripcion="Ventas por día del periodo consultado">
      <TableHead>
        <TableHeader>Fecha</TableHeader>
        <TableHeader className="text-right">Operaciones</TableHeader>
        <TableHeader className="text-right">Ventas</TableHeader>
        <TableHeader className="text-right">Costo</TableHeader>
        <TableHeader className="text-right">Margen bruto estimado</TableHeader>
      </TableHead>
      <TableBody>
        {reporte.periodo.por_dia.map((dia) => (
          <TableRow key={dia.fecha}>
            <TableCell className="numero">{formatearFecha(dia.fecha)}</TableCell>
            <TableCell numerica>{formatearNumero(dia.operaciones, 0)}</TableCell>
            <TableCell numerica>{formatearMoneda(dia.total)}</TableCell>
            <TableCell numerica>{formatearMoneda(dia.costo)}</TableCell>
            <TableCell numerica className="font-semibold">
              {formatearMoneda(dia.margen_bruto_estimado)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** Tabla de ventas por producto. */
export function TablaPorProducto({ reporte }: { reporte: ReporteVentas }) {
  if (reporte.por_producto.length === 0) {
    return <EmptyState titulo="Sin ventas por producto en el periodo" />;
  }

  return (
    <Table descripcion="Ventas por producto del periodo consultado">
      <TableHead>
        <TableHeader>Código</TableHeader>
        <TableHeader>Producto</TableHeader>
        <TableHeader className="text-right">Cantidad (base)</TableHeader>
        <TableHeader className="text-right">Ventas</TableHeader>
        <TableHeader className="text-right">Costo</TableHeader>
        <TableHeader className="text-right">Margen bruto estimado</TableHeader>
      </TableHead>
      <TableBody>
        {reporte.por_producto.map((fila) => (
          <TableRow key={fila.producto_id}>
            <TableCell className="numero text-xs text-muted">{fila.codigo}</TableCell>
            <TableCell className="font-semibold text-ink">{fila.producto}</TableCell>
            <TableCell numerica>{formatearCantidad(fila.cantidad_base)}</TableCell>
            <TableCell numerica>{formatearMoneda(fila.total)}</TableCell>
            <TableCell numerica>{formatearMoneda(fila.costo)}</TableCell>
            <TableCell numerica className="font-semibold">
              {formatearMoneda(fila.margen_bruto_estimado)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** Tabla de ventas por categoría. */
export function TablaPorCategoria({ reporte }: { reporte: ReporteVentas }) {
  if (reporte.por_categoria.length === 0) {
    return <EmptyState titulo="Sin ventas por categoría en el periodo" />;
  }

  return (
    <Table descripcion="Ventas por categoría del periodo consultado">
      <TableHead>
        <TableHeader>Categoría</TableHeader>
        <TableHeader className="text-right">Operaciones</TableHeader>
        <TableHeader className="text-right">Ventas</TableHeader>
        <TableHeader className="text-right">Costo</TableHeader>
        <TableHeader className="text-right">Margen bruto estimado</TableHeader>
      </TableHead>
      <TableBody>
        {reporte.por_categoria.map((fila) => (
          <TableRow key={fila.categoria}>
            <TableCell className="font-semibold text-ink">{fila.categoria}</TableCell>
            <TableCell numerica>{formatearNumero(fila.operaciones, 0)}</TableCell>
            <TableCell numerica>{formatearMoneda(fila.total)}</TableCell>
            <TableCell numerica>{formatearMoneda(fila.costo)}</TableCell>
            <TableCell numerica className="font-semibold">
              {formatearMoneda(fila.margen_bruto_estimado)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** Tabla de ventas por usuario. */
export function TablaPorUsuario({ reporte }: { reporte: ReporteVentas }) {
  if (reporte.por_usuario.length === 0) {
    return <EmptyState titulo="Sin ventas por usuario en el periodo" />;
  }

  return (
    <Table descripcion="Ventas por usuario del periodo consultado">
      <TableHead>
        <TableHeader>Usuario</TableHeader>
        <TableHeader className="text-right">Operaciones</TableHeader>
        <TableHeader className="text-right">Ventas</TableHeader>
      </TableHead>
      <TableBody>
        {reporte.por_usuario.map((fila) => (
          <TableRow key={fila.usuario}>
            <TableCell className="font-semibold text-ink">{fila.usuario}</TableCell>
            <TableCell numerica>{formatearNumero(fila.operaciones, 0)}</TableCell>
            <TableCell numerica>{formatearMoneda(fila.total)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** Tabla de abastecimientos agrupados por proveedor. */
export function TablaAbastecimientosPorProveedor({
  filas,
}: {
  filas: AbastecimientosPorProveedor[];
}) {
  if (filas.length === 0) {
    return (
      <EmptyState
        titulo="Sin abastecimientos en el periodo"
        descripcion="No se registraron ingresos de mercadería en las fechas consultadas."
      />
    );
  }

  return (
    <Table descripcion="Abastecimientos por proveedor del periodo consultado">
      <TableHead>
        <TableHeader>Proveedor</TableHeader>
        <TableHeader className="text-right">Operaciones</TableHeader>
        <TableHeader className="text-right">Total</TableHeader>
        <TableHeader>Último ingreso</TableHeader>
      </TableHead>
      <TableBody>
        {filas.map((fila) => (
          <TableRow key={fila.proveedor_id}>
            <TableCell className="font-semibold text-ink">{fila.proveedor}</TableCell>
            <TableCell numerica>{formatearNumero(fila.operaciones, 0)}</TableCell>
            <TableCell numerica>{formatearMoneda(fila.total)}</TableCell>
            <TableCell className="numero text-xs">
              {fila.ultimo_ingreso ? formatearFecha(fila.ultimo_ingreso) : '—'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** Tabla del histórico de costos de compra. */
export function TablaHistoricoCostos({ filas }: { filas: CostoHistoricoReporte[] }) {
  if (filas.length === 0) {
    return (
      <EmptyState
        titulo="Sin histórico de costos"
        descripcion="Todavía no hay compras confirmadas que generen historial de costos."
      />
    );
  }

  return (
    <div className="max-h-[420px] overflow-y-auto">
      <Table descripcion="Histórico de costos de compra">
        <TableHead>
          <TableHeader>Fecha</TableHeader>
          <TableHeader>Producto</TableHeader>
          <TableHeader>Proveedor</TableHeader>
          <TableHeader className="text-right">Cantidad</TableHeader>
          <TableHeader className="text-right">Costo unitario</TableHeader>
          <TableHeader className="text-right">Factor</TableHeader>
          <TableHeader>Documento</TableHeader>
        </TableHead>
        <TableBody>
          {filas.map((fila, indice) => (
            <TableRow key={`${fila.codigo}-${fila.fecha}-${indice}`}>
              <TableCell className="numero text-xs">{formatearFecha(fila.fecha)}</TableCell>
              <TableCell>
                <span className="font-semibold text-ink">{fila.producto}</span>
                <span className="ml-2 text-xs text-muted">{fila.codigo}</span>
              </TableCell>
              <TableCell className="text-xs">{fila.proveedor}</TableCell>
              <TableCell numerica>{formatearCantidad(fila.cantidad)}</TableCell>
              <TableCell numerica>{formatearMoneda(fila.costo_unitario)}</TableCell>
              <TableCell numerica>{formatearCantidad(fila.factor)}</TableCell>
              <TableCell className="text-xs">{fila.documento ?? '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Tabla del inventario valorizado a costo promedio. */
export function TablaInventarioValorizado({
  filas,
  total,
}: {
  filas: InventarioValorizado[];
  total: string;
}) {
  if (filas.length === 0) {
    return (
      <EmptyState
        titulo="Sin existencias valorizadas"
        descripcion="No hay productos con existencias registradas."
      />
    );
  }

  return (
    <>
      <div className="max-h-[420px] overflow-y-auto">
        <Table descripcion="Inventario valorizado a costo promedio">
          <TableHead>
            <TableHeader>Código</TableHeader>
            <TableHeader>Producto</TableHeader>
            <TableHeader className="text-right">Cantidad (base)</TableHeader>
            <TableHeader className="text-right">Costo promedio</TableHeader>
            <TableHeader className="text-right">Valor al costo</TableHeader>
          </TableHead>
          <TableBody>
            {filas.map((fila) => (
              <TableRow key={fila.producto_id}>
                <TableCell className="numero text-xs text-muted">{fila.codigo}</TableCell>
                <TableCell className="font-semibold text-ink">{fila.producto}</TableCell>
                <TableCell numerica>{formatearCantidad(fila.cantidad_base)}</TableCell>
                <TableCell numerica>{formatearMoneda(fila.costo_promedio_base)}</TableCell>
                <TableCell numerica className="font-semibold">
                  {formatearMoneda(fila.valor_costo)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-end border-t border-linea px-4 py-3">
        <span className="etiqueta mr-3">Valor total del inventario</span>
        <span className="text-xl font-bold numero text-ink">{formatearMoneda(total)}</span>
      </div>
    </>
  );
}

/** Envoltorio con estado de carga y error para las tablas de reporte. */
export function PanelConsulta({
  cargando,
  error,
  vacio,
  onReintentar,
  children,
}: {
  cargando: boolean;
  error: unknown;
  vacio?: boolean;
  onReintentar?: () => void;
  children: ReactNode;
}) {
  if (cargando) return <LoadingBlock etiqueta="Calculando…" />;
  if (error) {
    return (
      <div className="p-4">
        <Notice
          tono="error"
          titulo="No se pudo cargar la información"
          acciones={
            onReintentar ? (
              <button
                type="button"
                onClick={onReintentar}
                className="rounded-[6px] border border-linea-fuerte px-3 py-1.5 text-xs font-semibold"
              >
                Reintentar
              </button>
            ) : null
          }
        >
          {error instanceof Error ? error.message : 'Ocurrió un error inesperado.'}
        </Notice>
      </div>
    );
  }
  if (vacio) {
    return <EmptyState titulo="Sin datos en el periodo consultado" />;
  }
  return <>{children}</>;
}
