import { catalogoApi } from '@/shared/api/endpoints';
import type { Presentacion, Producto } from '@/shared/types/api';

export interface CoincidenciaCodigoBarras {
  producto: Producto;
  presentacion: Presentacion;
}

/**
 * Busca un código de barras exacto en el catálogo.
 *
 * El backend no expone un índice por código de barras, así que se recorren las
 * páginas del catálogo activo buscando la coincidencia exacta. La búsqueda es
 * local (servidor propio) y se detiene en la primera coincidencia.
 */
export async function buscarPorCodigoBarras(
  codigo: string,
  paginasMaximas = 30,
): Promise<CoincidenciaCodigoBarras | null> {
  const limpio = codigo.trim();
  if (limpio.length < 4) return null;

  const tamano = 200;
  for (let pagina = 1; pagina <= paginasMaximas; pagina += 1) {
    const respuesta = await catalogoApi.listarProductos({ pagina, tamano });
    for (const producto of respuesta.items) {
      const coincidentes = producto.presentaciones.filter(
        (item) => item.codigo_barras && item.codigo_barras.trim() === limpio,
      );
      // Se prefiere una presentación habilitada para la venta.
      const presentacion =
        coincidentes.find((item) => item.activo && item.es_venta) ?? coincidentes[0];
      if (presentacion) return { producto, presentacion };
    }
    if (respuesta.paginas < pagina) break;
  }

  return null;
}

/** Indica si el texto tiene forma de código de barras (dígitos, con_LONGitud razonable). */
export function pareceCodigoBarras(texto: string): boolean {
  const limpio = texto.trim();
  return /^\d{6,}$/.test(limpio);
}
