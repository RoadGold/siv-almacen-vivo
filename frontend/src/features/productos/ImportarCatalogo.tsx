import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
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
import { importacionApi } from '@/shared/api/endpoints';
import { formatearCantidad, formatearMoneda } from '@/shared/format/formato';
import { mensajeDeError } from '@/shared/hooks/errores';
import { registrarOperacion } from '@/shared/estado/operaciones';
import { guardarArchivo } from '@/shared/utils/descargas';
import type { PrevisualizacionImportacion, ResultadoImportacion } from '@/shared/types/api';

/**
 * Importación del catálogo desde Excel.
 *
 * El archivo NUNCA se aplica sin una confirmación explícita: primero se
 * previsualiza el resultado (resumen y errores por fila) y solo después el
 * usuario decide confirmar.
 */
export function ImportarCatalogo({ abierto, onCerrar }: { abierto: boolean; onCerrar: () => void }) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [previa, setPrevia] = useState<PrevisualizacionImportacion | null>(null);
  const [resultado, setResultado] = useState<ResultadoImportacion | null>(null);
  const [aplicarStockInicial, setAplicarStockInicial] = useState(false);
  const [descargandoPlantilla, setDescargandoPlantilla] = useState(false);

  const referenciaArchivo = useRef<HTMLInputElement>(null);
  const cliente = useQueryClient();
  const { notificar } = useToast();

  const previsualizar = useMutation({
    mutationFn: (fichero: File) => importacionApi.previsualizar(fichero),
    onSuccess: (datos) => {
      setPrevia(datos);
      setResultado(null);
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  const confirmar = useMutation({
    mutationFn: (fichero: File) =>
      importacionApi.confirmar(fichero, { aplicarStockInicial }),
    onSuccess: (datos) => {
      setResultado(datos);
      setPrevia(null);
      registrarOperacion(
        `Importación de catálogo: ${datos.productos_creados} creados, ${datos.productos_actualizados} actualizados`,
      );
      notificar(
        `Importación aplicada: ${datos.importadas} fila(s) importada(s), ${datos.rechazadas} rechazada(s).`,
        'exito',
      );
      cliente.invalidateQueries({ queryKey: ['catalogo'] });
      cliente.invalidateQueries({ queryKey: ['inventario'] });
    },
    onError: (error) => notificar(mensajeDeError(error), 'error'),
  });

  async function descargarPlantilla() {
    setDescargandoPlantilla(true);
    try {
      const archivoPlantilla = await importacionApi.plantilla();
      guardarArchivo(archivoPlantilla, 'plantilla-catalogo-siv.xlsx');
      notificar('Se descargó la plantilla del catálogo.', 'exito');
    } catch (error) {
      notificar(mensajeDeError(error), 'error');
    } finally {
      setDescargandoPlantilla(false);
    }
  }

  function cerrar() {
    setArchivo(null);
    setPrevia(null);
    setResultado(null);
    setAplicarStockInicial(false);
    if (referenciaArchivo.current) referenciaArchivo.current.value = '';
    onCerrar();
  }

  return (
    <Modal
      abierto={abierto}
      titulo="Importar catálogo desde Excel"
      descripcion="Descarga la plantilla, completa el archivo y revisa la vista previa antes de aplicar."
      ancho="xl"
      onCerrar={cerrar}
      pie={
        resultado ? (
          <Button variante="secundario" onClick={cerrar}>
            Cerrar
          </Button>
        ) : (
          <>
            <Button variante="secundario" onClick={cerrar}>
              Cancelar
            </Button>
            {previa ? (
              <>
                <Button
                  variante="secundario"
                  disabled={previsualizar.isPending}
                  onClick={() => archivo && previsualizar.mutate(archivo)}
                >
                  Volver a previsualizar
                </Button>
                <Button
                  variante="primario"
                  disabled={!archivo || confirmar.isPending || previa.resumen.filas === 0}
                  cargando={confirmar.isPending}
                  textoCargando="Aplicando importación…"
                  onClick={() => archivo && confirmar.mutate(archivo)}
                >
                  Confirmar y aplicar ({previa.resumen.filas} fila(s))
                </Button>
              </>
            ) : (
              <Button
                variante="primario"
                disabled={!archivo || previsualizar.isPending}
                cargando={previsualizar.isPending}
                textoCargando="Analizando archivo…"
                onClick={() => archivo && previsualizar.mutate(archivo)}
              >
                Previsualizar
              </Button>
            )}
          </>
        )
      }
    >
      <div className="flex flex-col gap-4">
        {/* --- Paso 1: plantilla y archivo --- */}
        <Card titulo="1 · Archivo">
          <CardBody className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variante="secundario"
                cargando={descargandoPlantilla}
                textoCargando="Descargando…"
                onClick={() => void descargarPlantilla()}
              >
                Descargar plantilla
              </Button>
              <p className="text-xs text-muted">
                La plantilla trae las columnas esperadas y un ejemplo de cada una.
              </p>
            </div>

            <div>
              <label htmlFor="archivo-importacion" className="mb-1 block text-sm font-semibold">
                Archivo Excel o CSV (`.xlsx`, `.csv`)
              </label>
              <input
                id="archivo-importacion"
                ref={referenciaArchivo}
                type="file"
                accept=".xlsx,.xlsm,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                className="block w-full text-sm text-ink file:mr-3 file:rounded-[6px] file:border file:border-linea-fuerte file:bg-surface file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-ink"
                onChange={(evento) => {
                  const fichero = evento.target.files?.[0] ?? null;
                  setArchivo(fichero);
                  setPrevia(null);
                  setResultado(null);
                }}
              />
              {archivo ? (
                <p className="mt-1 text-xs text-muted">
                  Archivo seleccionado: <span className="font-semibold text-ink">{archivo.name}</span>
                </p>
              ) : null}
            </div>

            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={aplicarStockInicial}
                onChange={(evento) => setAplicarStockInicial(evento.target.checked)}
              />
              Aplicar también el stock inicial indicado en el archivo
              <span className="text-xs text-muted">
                (genera movimientos de «saldo inicial»; no es una compra). Se aplica una sola vez
                por producto y solo si el producto todavía no tiene existencias.
              </span>
            </label>
          </CardBody>
        </Card>

        {/* --- Paso 2: vista previa --- */}
        {previa ? (
          <Card titulo="2 · Vista previa" subtitulo="Nada se ha escrito todavía en la base de datos">
            <CardBody className="flex flex-col gap-3">
              <div className="grid gap-3 sm:grid-cols-4">
                <Contador titulo="Filas" valor={previa.resumen.filas} />
                <Contador titulo="Productos nuevos" valor={previa.resumen.nuevos} tono="marca" />
                <Contador titulo="A actualizar" valor={previa.resumen.actualizar} tono="aviso" />
                <Contador titulo="Con errores" valor={previa.resumen.con_errores} tono="peligro" />
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <Contador titulo="Con avisos" valor={previa.resumen.con_avisos} tono="aviso" />
                <Contador
                  titulo="Con stock inicial"
                  valor={previa.resumen.con_stock_inicial}
                  tono="marca"
                />
                <Contador
                  titulo="Vínculos de proveedor"
                  valor={previa.resumen.vinculos_proveedor}
                  tono="marca"
                />
              </div>

              {previa.resumen.con_avisos > 0 ? (
                <Notice tono="aviso" titulo="Hay avisos que conviene revisar">
                  Los avisos no impiden la importación, pero indican situaciones que podrían
                  sorprender: stock inicial repetido entre filas del mismo producto, productos que
                  ya tienen existencias o posibles artículos duplicados.
                </Notice>
              ) : null}

              {previa.resumen.con_errores > 0 ? (
                <Notice tono="aviso" titulo="Algunas filas tienen errores">
                  Las filas con errores se omiten al aplicar la importación. Revísalas y corrige el
                  archivo si lo necesitas.
                </Notice>
              ) : null}

              {previa.filas.length === 0 ? (
                <EmptyState
                  titulo="El archivo no contiene filas"
                  descripcion="Revisa que hayas usado la plantilla y que las filas tengan datos."
                />
              ) : (
                <div className="max-h-[320px] overflow-auto">
                  <Table descripcion="Filas del archivo a importar">
                    <TableHead>
                      <TableHeader>Fila</TableHeader>
                      <TableHeader>Código</TableHeader>
                      <TableHeader>Producto</TableHeader>
                      <TableHeader>Categoría</TableHeader>
                      <TableHeader>Presentación</TableHeader>
                      <TableHeader className="text-right">Factor</TableHeader>
                      <TableHeader className="text-right">Precio</TableHeader>
                      <TableHeader className="text-right">Stock inicial</TableHeader>
                      <TableHeader>Proveedor</TableHeader>
                      <TableHeader>Estado</TableHeader>
                      <TableHeader>Errores</TableHeader>
                      <TableHeader>Avisos</TableHeader>
                    </TableHead>
                    <TableBody>
                      {previa.filas.map((fila) => (
                        <TableRow key={fila.numero}>
                          <TableCell className="numero text-xs">{fila.numero}</TableCell>
                          <TableCell className="numero text-xs">{fila.codigo || '—'}</TableCell>
                          <TableCell className="text-xs">{fila.nombre || '—'}</TableCell>
                          <TableCell className="text-xs">{fila.categoria || '—'}</TableCell>
                          <TableCell className="text-xs">{fila.presentacion || '—'}</TableCell>
                          <TableCell numerica className="text-xs">
                            {fila.factor_base ? formatearCantidad(fila.factor_base) : '—'}
                          </TableCell>
                          <TableCell numerica className="text-xs">
                            {fila.precio_venta ? formatearMoneda(fila.precio_venta) : '—'}
                          </TableCell>
                          <TableCell numerica className="text-xs">
                            {fila.stock_inicial ? formatearCantidad(fila.stock_inicial) : '—'}
                          </TableCell>
                          <TableCell className="text-xs">
                            {fila.proveedor_codigo || '—'}
                          </TableCell>
                          <TableCell>
                            <EtiquetaEstadoImportacion estado={fila.estado} />
                          </TableCell>
                          <TableCell className="text-xs text-danger">
                            {fila.mensajes.length > 0 ? fila.mensajes.join(' · ') : '—'}
                          </TableCell>
                          <TableCell className="text-xs text-warning">
                            {fila.avisos.length > 0 ? fila.avisos.join(' · ') : '—'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              <Notice tono="info" titulo="Confirmación explícita">
                Al pulsar «Confirmar y aplicar» se crearán o actualizarán los productos del
                archivo. Revisa el resumen antes de continuar.
              </Notice>
            </CardBody>
          </Card>
        ) : null}

        {/* --- Paso 3: resultado --- */}
        {resultado ? (
          <Card titulo="3 · Resultado de la importación">
            <CardBody className="flex flex-col gap-3">
              <div className="grid gap-3 sm:grid-cols-4">
                <Contador titulo="Filas importadas" valor={resultado.importadas} tono="marca" />
                <Contador titulo="Productos creados" valor={resultado.productos_creados} tono="marca" />
                <Contador
                  titulo="Productos actualizados"
                  valor={resultado.productos_actualizados}
                  tono="aviso"
                />
                <Contador titulo="Rechazadas" valor={resultado.rechazadas} tono="peligro" />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Contador
                  titulo="Saldos iniciales cargados"
                  valor={resultado.stock_inicial_aplicado}
                  tono="marca"
                />
                <Contador
                  titulo="Vínculos de proveedor"
                  valor={resultado.vinculos_proveedor}
                  tono="marca"
                />
              </div>

              {resultado.stock_inicial_aplicado === 0 && aplicarStockInicial ? (
                <Notice tono="aviso" titulo="No se cargó ningún saldo inicial">
                  Ningún producto del archivo recibió saldo inicial: probablemente ya tenían
                  existencias registradas. Use un ajuste de inventario si necesita corregirlos.
                </Notice>
              ) : null}

              {resultado.errores.length > 0 ? (
                <div>
                  <h4 className="etiqueta mb-1">Filas con errores</h4>
                  <ul className="divide-y divide-linea rounded-[6px] border border-linea">
                    {resultado.errores.map((fila) => (
                      <li key={fila.numero} className="px-3 py-2 text-xs">
                        <span className="numero font-semibold text-ink">Fila {fila.numero}</span>{' '}
                        <span className="text-muted">
                          {fila.codigo || fila.nombre || 'sin código'}
                        </span>{' '}
                        <span className="text-danger">{fila.mensajes.join(' · ')}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </CardBody>
          </Card>
        ) : null}
      </div>
    </Modal>
  );
}

/** Etiqueta del estado de una fila de importación. */
function EtiquetaEstadoImportacion({ estado }: { estado: string }) {
  const tono =
    estado === 'nuevo'
      ? 'marca'
      : estado === 'actualizar'
        ? 'aviso'
        : estado === 'error'
          ? 'peligro'
          : 'neutro';
  const texto =
    estado === 'nuevo'
      ? 'Nuevo'
      : estado === 'actualizar'
        ? 'Actualizar'
        : estado === 'error'
          ? 'Con error'
          : estado;
  return <Badge tono={tono}>{texto}</Badge>;
}

/** Contador del resumen de la importación. */
function Contador({
  titulo,
  valor,
  tono,
}: {
  titulo: string;
  valor: number;
  tono?: 'marca' | 'aviso' | 'peligro';
}) {
  const color =
    tono === 'marca'
      ? 'text-brand'
      : tono === 'aviso'
        ? 'text-warning'
        : tono === 'peligro'
          ? 'text-danger'
          : 'text-ink';
  return (
    <div className="rounded-[6px] border border-linea px-4 py-3">
      <p className="etiqueta">{titulo}</p>
      <p className={`mt-1 text-2xl font-bold numero ${color}`}>{valor}</p>
    </div>
  );
}
