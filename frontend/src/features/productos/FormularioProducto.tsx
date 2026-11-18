import { useMemo, useState } from 'react';
import { Button, Field, Input, Notice, Select } from '@/design-system';
import { Decimal } from '@/shared/format/decimal';
import { formatearCantidad, formatearMoneda } from '@/shared/format/formato';
import type { Categoria, UnidadMedida } from '@/shared/types/api';

export interface PresentacionFormulario {
  nombre: string;
  factor_base: string;
  precio_venta: string;
  costo_referencia: string;
  es_compra: boolean;
  es_venta: boolean;
  permite_fraccion: boolean;
}

export interface DatosProductoFormulario {
  codigo: string;
  nombre: string;
  descripcion: string | null;
  categoria_id: number | null;
  unidad_base_id: number;
  stock_minimo_base: string;
  permite_fraccion: boolean;
  activo: boolean;
  presentaciones: PresentacionFormulario[];
}

interface Propiedades {
  unidades: UnidadMedida[];
  categorias: Categoria[];
  onCancelar: () => void;
  onEnviar: (datos: DatosProductoFormulario) => void;
  guardando: boolean;
  error: string | null;
}

const PRESENTACION_VACIA: PresentacionFormulario = {
  nombre: '',
  factor_base: '1',
  precio_venta: '0',
  costo_referencia: '0',
  es_compra: true,
  es_venta: true,
  permite_fraccion: false,
};

/** Formulario de alta de producto con sus presentaciones y ejemplo de conversión en vivo. */
export function FormularioProducto({
  unidades,
  categorias,
  onCancelar,
  onEnviar,
  guardando,
  error,
}: Propiedades) {
  const [codigo, setCodigo] = useState('');
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [categoriaId, setCategoriaId] = useState<number | ''>('');
  const [unidadId, setUnidadId] = useState<number | ''>(unidades[0]?.id ?? '');
  const [stockMinimo, setStockMinimo] = useState('0');
  const [permiteFraccion, setPermiteFraccion] = useState(false);
  const [presentaciones, setPresentaciones] = useState<PresentacionFormulario[]>([
    { ...PRESENTACION_VACIA },
  ]);

  const unidad = useMemo(
    () => unidades.find((item) => item.id === unidadId),
    [unidades, unidadId],
  );

  function cambiarPresentacion(indice: number, campo: keyof PresentacionFormulario, valor: string) {
    setPresentaciones((actuales) =>
      actuales.map((item, posicion) =>
        posicion === indice ? { ...item, [campo]: valor } : item,
      ),
    );
  }

  function agregarPresentacion() {
    setPresentaciones((actuales) => [...actuales, { ...PRESENTACION_VACIA }]);
  }

  function quitarPresentacion(indice: number) {
    setPresentaciones((actuales) => actuales.filter((_, posicion) => posicion !== indice));
  }

  const errores: string[] = [];
  if (!codigo.trim()) errores.push('El código es obligatorio.');
  if (!nombre.trim()) errores.push('El nombre es obligatorio.');
  if (!unidadId) errores.push('Debe elegirse una unidad base.');
  const presentacionesValidas = presentaciones.filter(
    (item) => item.nombre.trim() && Decimal.desde(item.factor_base).comparar(0) > 0,
  );
  if (presentacionesValidas.length !== presentaciones.length) {
    errores.push('Cada presentación necesita nombre y un factor de conversión mayor que cero.');
  }

  function enviar() {
    if (errores.length > 0) return;
    onEnviar({
      codigo: codigo.trim(),
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      categoria_id: categoriaId === '' ? null : categoriaId,
      unidad_base_id: Number(unidadId),
      stock_minimo_base: stockMinimo || '0',
      permite_fraccion: permiteFraccion,
      activo: true,
      presentaciones: presentacionesValidas.map((item) => ({
        nombre: item.nombre.trim(),
        factor_base: Decimal.desde(item.factor_base).aTexto(),
        precio_venta: Decimal.desde(item.precio_venta).aTexto(),
        costo_referencia: Decimal.desde(item.costo_referencia).aTexto(),
        es_compra: item.es_compra,
        es_venta: item.es_venta,
        permite_fraccion: item.permite_fraccion,
      })),
    });
  }

  return (
    <div className="flex flex-col gap-4">
      {error ? (
        <Notice tono="error" titulo="No se pudo guardar el producto">
          {error}
        </Notice>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        <Field htmlFor="producto-codigo" etiqueta="Código" ejemplo="ARZ-001" obligatorio>
          <Input
            id="producto-codigo"
            value={codigo}
            onChange={(evento) => setCodigo(evento.target.value)}
          />
        </Field>
        <Field htmlFor="producto-nombre" etiqueta="Nombre" ejemplo="Arroz a granel" obligatorio>
          <Input
            id="producto-nombre"
            value={nombre}
            onChange={(evento) => setNombre(evento.target.value)}
          />
        </Field>
        <Field
          htmlFor="producto-unidad"
          etiqueta="Unidad base"
          ayuda="Ejemplo: UND (unidades), GR (gramos) o ML (mililitros)."
          obligatorio
        >
          <Select
            id="producto-unidad"
            value={unidadId}
            onChange={(evento) => setUnidadId(Number(evento.target.value))}
          >
            <option value="">Selecciona una unidad…</option>
            {unidades.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nombre}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          htmlFor="producto-categoria"
          etiqueta="Categoría"
          ayuda="Ejemplo: Abarrotes."
        >
          <Select
            id="producto-categoria"
            value={categoriaId}
            onChange={(evento) => setCategoriaId(Number(evento.target.value))}
          >
            <option value="">Sin categoría</option>
            {categorias.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nombre}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          htmlFor="producto-stock-minimo"
          etiqueta="Stock mínimo"
          ejemplo="10000"
          ayuda={`Expresado en ${unidad?.nombre.toLowerCase() ?? 'unidad base'}.`}
        >
          <Input
            id="producto-stock-minimo"
            className="numero"
            inputMode="decimal"
            value={stockMinimo}
            onChange={(evento) => setStockMinimo(evento.target.value)}
          />
        </Field>
        <Field
          htmlFor="producto-descripcion"
          etiqueta="Descripción"
          ejemplo="Arroz pilado de la marca Genérica"
        >
          <Input
            id="producto-descripcion"
            value={descripcion}
            onChange={(evento) => setDescripcion(evento.target.value)}
          />
        </Field>
      </div>

      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={permiteFraccion}
          onChange={(evento) => setPermiteFraccion(evento.target.checked)}
        />
        Permitir vender fracciones del producto
      </label>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink">Presentaciones</h3>
          <Button variante="secundario" tamano="sm" onClick={agregarPresentacion}>
            Añadir presentación
          </Button>
        </div>

        <p className="text-xs text-muted">
          Cada presentación define una equivalencia exacta con la unidad base y su precio de venta.
        </p>

        {presentaciones.map((presentacion, indice) => (
          <div
            key={indice}
            className="flex flex-col gap-2 rounded-[6px] border border-linea px-3 py-3"
          >
            <div className="grid gap-2 md:grid-cols-4">
              <Field
                htmlFor={`presentacion-nombre-${indice}`}
                etiqueta="Nombre"
                ejemplo="Saco 50 kg"
                compacto
              >
                <Input
                  id={`presentacion-nombre-${indice}`}
                  value={presentacion.nombre}
                  onChange={(evento) =>
                    cambiarPresentacion(indice, 'nombre', evento.target.value)
                  }
                />
              </Field>
              <Field
                htmlFor={`presentacion-factor-${indice}`}
                etiqueta="Factor de conversión"
                ejemplo="24"
                ayuda={`1 presentación = ${formatearCantidad(presentacion.factor_base)} ${unidad?.nombre.toLowerCase() ?? 'unidad base'}`}
                compacto
              >
                <Input
                  id={`presentacion-factor-${indice}`}
                  className="numero"
                  inputMode="decimal"
                  value={presentacion.factor_base}
                  onChange={(evento) =>
                    cambiarPresentacion(indice, 'factor_base', evento.target.value)
                  }
                />
              </Field>
              <Field
                htmlFor={`presentacion-precio-${indice}`}
                etiqueta="Precio de venta"
                ejemplo="48.00"
                compacto
              >
                <Input
                  id={`presentacion-precio-${indice}`}
                  className="numero"
                  inputMode="decimal"
                  prefijo="S/"
                  value={presentacion.precio_venta}
                  onChange={(evento) =>
                    cambiarPresentacion(indice, 'precio_venta', evento.target.value)
                  }
                />
              </Field>
              <Field
                htmlFor={`presentacion-costo-${indice}`}
                etiqueta="Costo de referencia"
                ejemplo="36.00"
                compacto
              >
                <Input
                  id={`presentacion-costo-${indice}`}
                  className="numero"
                  inputMode="decimal"
                  prefijo="S/"
                  value={presentacion.costo_referencia}
                  onChange={(evento) =>
                    cambiarPresentacion(indice, 'costo_referencia', evento.target.value)
                  }
                />
              </Field>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-1.5 text-xs text-ink">
                <input
                  type="checkbox"
                  checked={presentacion.es_compra}
                  onChange={(evento) =>
                    setPresentaciones((actuales) =>
                      actuales.map((item, posicion) =>
                        posicion === indice
                          ? { ...item, es_compra: evento.target.checked }
                          : item,
                      ),
                    )
                  }
                />
                Para comprar
              </label>
              <label className="flex items-center gap-1.5 text-xs text-ink">
                <input
                  type="checkbox"
                  checked={presentacion.es_venta}
                  onChange={(evento) =>
                    setPresentaciones((actuales) =>
                      actuales.map((item, posicion) =>
                        posicion === indice
                          ? { ...item, es_venta: evento.target.checked }
                          : item,
                      ),
                    )
                  }
                />
                Para vender
              </label>
              <label className="flex items-center gap-1.5 text-xs text-ink">
                <input
                  type="checkbox"
                  checked={presentacion.permite_fraccion}
                  onChange={(evento) =>
                    setPresentaciones((actuales) =>
                      actuales.map((item, posicion) =>
                        posicion === indice
                          ? { ...item, permite_fraccion: evento.target.checked }
                          : item,
                      ),
                    )
                  }
                />
                Admite fracciones
              </label>

              <p className="text-xs font-semibold text-brand">
                Ejemplo: 1 {presentacion.nombre || 'presentación'} ={' '}
                {formatearCantidad(presentacion.factor_base)}{' '}
                {unidad?.nombre.toLowerCase() ?? 'unidad base'} ·{' '}
                {formatearMoneda(presentacion.precio_venta)}
              </p>

              {presentaciones.length > 1 ? (
                <Button
                  variante="fantasma"
                  tamano="sm"
                  onClick={() => quitarPresentacion(indice)}
                  className="ml-auto"
                >
                  Quitar
                </Button>
              ) : null}
            </div>
          </div>
        ))}
      </section>

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
          onClick={enviar}
        >
          Guardar producto
        </Button>
      </div>
    </div>
  );
}
