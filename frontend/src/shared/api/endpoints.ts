/**
 * Endpoints del API de SIV · Almacén Vivo.
 * Un único lugar donde vive la forma de llamar al backend.
 */

import { api, consultarSalud } from './client';
import type {
  Abastecimiento,
  AbastecimientoIn,
  Categoria,
  Existencia,
  Marca,
  Movimiento,
  Pagina,
  PrevisualizacionAbastecimiento,
  PrevisualizacionVenta,
  Presentacion,
  PresentacionIn,
  Producto,
  ProductoDelProveedor,
  ProductoFicha,
  Proveedor,
  RadarReposicion,
  RespuestaLogin,
  ResumenDashboard,
  UnidadMedida,
  Usuario,
  Venta,
  VentaIn,
  VinculoProductoProveedor,
} from '../types/api';

export const authApi = {
  entrar: (usuario: string, password: string) =>
    api.post<RespuestaLogin>('/auth/login', { usuario, password }),
  yo: () => api.get<Usuario>('/auth/me'),
  salir: () => api.post<{ mensaje: string }>('/auth/logout'),
};

export interface FiltroProductos {
  q?: string;
  categoria_id?: number | null;
  marca_id?: number | null;
  activo?: boolean | null;
  pagina?: number;
  tamano?: number;
}

export const catalogoApi = {
  listarProductos: (filtros: FiltroProductos = {}) =>
    api.get<Pagina<Producto>>('/catalogo/productos', {
      q: filtros.q,
      categoria_id: filtros.categoria_id ?? undefined,
      marca_id: filtros.marca_id ?? undefined,
      activo: filtros.activo === null ? undefined : filtros.activo,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 20,
    }),
  obtenerProducto: (id: number) => api.get<Producto>(`/catalogo/productos/${id}`),
  crearProducto: (cuerpo: {
    codigo: string;
    nombre: string;
    descripcion?: string | null;
    categoria_id?: number | null;
    marca_id?: number | null;
    unidad_base_id: number;
    stock_minimo_base: string;
    permite_fraccion: boolean;
    activo: boolean;
    presentaciones: PresentacionIn[];
  }) => api.post<Producto>('/catalogo/productos', cuerpo),
  actualizarProducto: (
    id: number,
    cambios: {
      nombre?: string;
      descripcion?: string | null;
      categoria_id?: number | null;
      stock_minimo_base?: string;
      permite_fraccion?: boolean;
      activo?: boolean;
    },
  ) => api.patch<Producto>(`/catalogo/productos/${id}`, cambios),
  agregarPresentacion: (
    productoId: number,
    cuerpo: {
      nombre: string;
      factor_base: string;
      precio_venta: string;
      costo_referencia?: string;
      codigo_barras?: string | null;
      es_compra: boolean;
      es_venta: boolean;
      permite_fraccion: boolean;
    },
  ) => api.post<Presentacion>(`/catalogo/productos/${productoId}/presentaciones`, cuerpo),
  unidades: () => api.get<UnidadMedida[]>('/catalogo/unidades'),
  categorias: () => api.get<Categoria[]>('/catalogo/categorias'),
  marcas: () => api.get<Marca[]>('/catalogo/marcas'),
};

export interface FiltroProveedores {
  q?: string;
  activo?: boolean | null;
  pagina?: number;
  tamano?: number;
}

export const proveedoresApi = {
  listar: (filtros: FiltroProveedores = {}) =>
    api.get<Pagina<Proveedor>>('/proveedores', {
      q: filtros.q,
      activo: filtros.activo === null ? undefined : filtros.activo,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 20,
    }),
  obtener: (id: number) => api.get<Proveedor>(`/proveedores/${id}`),
  crear: (cuerpo: {
    codigo: string;
    razon_social: string;
    nombre_comercial?: string | null;
    ruc?: string | null;
    telefono?: string | null;
    contacto?: string | null;
    direccion?: string | null;
    email?: string | null;
    observaciones?: string | null;
    activo: boolean;
  }) => api.post<Proveedor>('/proveedores', cuerpo),
  actualizar: (
    id: number,
    cambios: Partial<{
      razon_social: string;
      nombre_comercial: string | null;
      ruc: string | null;
      telefono: string | null;
      contacto: string | null;
      direccion: string | null;
      email: string | null;
      observaciones: string | null;
      activo: boolean;
    }>,
  ) => api.patch<Proveedor>(`/proveedores/${id}`, cambios),
  productos: (id: number) => api.get<ProductoDelProveedor[]>(`/proveedores/${id}/productos`),
  historial: (id: number, limite = 20) =>
    api.get<
      {
        id: number;
        numero: string;
        fecha: string;
        documento?: string | null;
        estado: string;
        total: string;
      }[]
    >(`/proveedores/${id}/historial`, { limite }),
  vincularProducto: (cuerpo: {
    producto_id: number;
    proveedor_id: number;
    habitual: boolean;
    presentacion_id?: number | null;
    observacion?: string | null;
  }) => api.post<VinculoProductoProveedor>('/proveedores/vinculos', cuerpo),
};

export interface FiltroExistencias {
  almacen_id?: number | null;
  q?: string;
  categoria_id?: number | null;
  estado?: string | null;
  pagina?: number;
  tamano?: number;
}

export const inventarioApi = {
  existencias: (filtros: FiltroExistencias = {}) =>
    api.get<Pagina<Existencia>>('/inventario/existencias', {
      almacen_id: filtros.almacen_id ?? undefined,
      q: filtros.q,
      categoria_id: filtros.categoria_id ?? undefined,
      estado: filtros.estado ?? undefined,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 25,
    }),
  ficha: (productoId: number) => api.get<ProductoFicha>(`/inventario/productos/${productoId}/ficha`),
  movimientos: (filtros: { producto_id?: number; tipo?: string; pagina?: number; tamano?: number }) =>
    api.get<Pagina<Movimiento>>('/inventario/movimientos', {
      producto_id: filtros.producto_id,
      tipo: filtros.tipo,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 50,
    }),
  radar: (limite = 25) => api.get<RadarReposicion[]>('/inventario/radar-reposicion', { limite }),
};

export const ventasApi = {
  previsualizar: (cuerpo: VentaIn) =>
    api.post<PrevisualizacionVenta>('/ventas/previsualizar', cuerpo),
  confirmar: (cuerpo: VentaIn) => api.post<Venta>('/ventas', cuerpo),
  listar: (filtros: { desde?: string; hasta?: string; estado?: string; pagina?: number; tamano?: number }) =>
    api.get<Pagina<Venta>>('/ventas', {
      desde: filtros.desde,
      hasta: filtros.hasta,
      estado: filtros.estado,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 5,
    }),
  obtener: (id: number) => api.get<Venta>(`/ventas/${id}`),
};

export const abastecimientosApi = {
  previsualizar: (cuerpo: AbastecimientoIn) =>
    api.post<PrevisualizacionAbastecimiento>('/abastecimientos/previsualizar', cuerpo),
  confirmar: (cuerpo: AbastecimientoIn) =>
    api.post<Abastecimiento>('/abastecimientos', cuerpo),
  listar: (filtros: { proveedor_id?: number; pagina?: number; tamano?: number }) =>
    api.get<Pagina<Abastecimiento>>('/abastecimientos', {
      proveedor_id: filtros.proveedor_id,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 5,
    }),
};

export const dashboardApi = {
  resumen: () => api.get<ResumenDashboard>('/dashboard/resumen'),
};

export const sistemaApi = {
  /** El endpoint de salud vive fuera del prefijo `/api/v1` y no requiere token. */
  salud: () => consultarSalud(),
};
