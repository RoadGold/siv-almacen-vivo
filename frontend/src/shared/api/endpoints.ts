/**
 * Endpoints del API de SIV · Almacén Vivo.
 * Un único lugar donde vive la forma de llamar al backend.
 */

import { api, consultarSalud, descargar, enviarFormulario } from './client';
import type {
  Abastecimiento,
  AbastecimientoIn,
  AbastecimientosPorProveedor,
  Categoria,
  CostoHistoricoReporte,
  Existencia,
  InventarioValorizado,
  Marca,
  MargenBruto,
  Movimiento,
  Pagina,
  PrevisualizacionAbastecimiento,
  PrevisualizacionImportacion,
  PrevisualizacionVenta,
  Presentacion,
  PresentacionIn,
  Producto,
  ProductoDelProveedor,
  ProductoFicha,
  Proveedor,
  RadarReposicion,
  RegistroAuditoria,
  ReporteVentas,
  RespuestaLogin,
  ResultadoImportacion,
  ResultadoInventarioInicial,
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
  movimientos: (filtros: {
    producto_id?: number | null;
    almacen_id?: number | null;
    tipo?: string | null;
    desde?: string | null;
    hasta?: string | null;
    pagina?: number;
    tamano?: number;
  }) =>
    api.get<Pagina<Movimiento>>('/inventario/movimientos', {
      producto_id: filtros.producto_id ?? undefined,
      almacen_id: filtros.almacen_id ?? undefined,
      tipo: filtros.tipo ?? undefined,
      desde: filtros.desde ?? undefined,
      hasta: filtros.hasta ?? undefined,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 50,
    }),
  radar: (limite = 25) => api.get<RadarReposicion[]>('/inventario/radar-reposicion', { limite }),
  /** Carga inicial de existencias: es una operación administrativa, no una compra. */
  inventarioInicial: (cuerpo: {
    almacen_id?: number | null;
    referencia?: string;
    lineas: { producto_id: number; cantidad_base: string; costo_unitario_base: string }[];
  }) => api.post<ResultadoInventarioInicial>('/inventario/inventario-inicial', cuerpo),
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
  obtener: (id: number) => api.get<Abastecimiento>(`/abastecimientos/${id}`),
};

export const dashboardApi = {
  resumen: () => api.get<ResumenDashboard>('/dashboard/resumen'),
};

/* --- Reportes ------------------------------------------------------- */

export interface FiltroPeriodo {
  desde?: string | null;
  hasta?: string | null;
}

export const reportesApi = {
  ventas: (filtro: FiltroPeriodo = {}) =>
    api.get<ReporteVentas>('/reportes/ventas', {
      desde: filtro.desde ?? undefined,
      hasta: filtro.hasta ?? undefined,
    }),
  abastecimientos: (filtro: FiltroPeriodo = {}) =>
    api.get<AbastecimientosPorProveedor[]>('/reportes/abastecimientos', {
      desde: filtro.desde ?? undefined,
      hasta: filtro.hasta ?? undefined,
    }),
  costos: (filtro: { producto_id?: number | null; proveedor_id?: number | null } = {}) =>
    api.get<CostoHistoricoReporte[]>('/reportes/costos', {
      producto_id: filtro.producto_id ?? undefined,
      proveedor_id: filtro.proveedor_id ?? undefined,
    }),
  inventario: (almacen_id?: number | null) =>
    api.get<InventarioValorizado[]>('/reportes/inventario', {
      almacen_id: almacen_id ?? undefined,
    }),
  margen: (filtro: FiltroPeriodo = {}) =>
    api.get<MargenBruto>('/reportes/margen', {
      desde: filtro.desde ?? undefined,
      hasta: filtro.hasta ?? undefined,
    }),
  /** Descarga el detalle de ventas del periodo en CSV. */
  exportarVentasCsv: (filtro: FiltroPeriodo = {}) =>
    descargar('/reportes/ventas/exportar', {
      desde: filtro.desde ?? undefined,
      hasta: filtro.hasta ?? undefined,
    }),
};

/* --- Administración -------------------------------------------------- */

export const adminApi = {
  usuarios: (filtros: { activo?: boolean | null; pagina?: number; tamano?: number } = {}) =>
    api.get<Pagina<Usuario>>('/admin/usuarios', {
      activo: filtros.activo === null ? undefined : filtros.activo,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 20,
    }),
  crearUsuario: (cuerpo: {
    nombre: string;
    usuario: string;
    password: string;
    rol: string;
    activo: boolean;
  }) => api.post<Usuario>('/admin/usuarios', cuerpo),
  actualizarUsuario: (
    id: number,
    cambios: {
      nombre?: string;
      password?: string;
      activo?: boolean;
      rol?: string;
    },
  ) => api.patch<Usuario>(`/admin/usuarios/${id}`, cambios),
  auditoria: (filtros: { entidad?: string | null; pagina?: number; tamano?: number } = {}) =>
    api.get<Pagina<RegistroAuditoria>>('/admin/auditoria', {
      entidad: filtros.entidad ?? undefined,
      pagina: filtros.pagina ?? 1,
      tamano: filtros.tamano ?? 50,
    }),
};

/* --- Importación de catálogo ---------------------------------------- */

export const importacionApi = {
  /** Descarga la plantilla Excel del catálogo. */
  plantilla: () => descargar('/catalogo/importar/plantilla'),
  /** Analiza el archivo sin escribir nada en la base de datos. */
  previsualizar: (archivo: File) => {
    const datos = new FormData();
    datos.append('archivo', archivo);
    return enviarFormulario<PrevisualizacionImportacion>('/catalogo/importar/previsualizar', datos);
  },
  /** Aplica las filas válidas del archivo (requiere confirmación del usuario). */
  confirmar: (archivo: File, opciones: { aplicarStockInicial: boolean; almacenId?: number | null }) => {
    const datos = new FormData();
    datos.append('archivo', archivo);
    return enviarFormulario<ResultadoImportacion>('/catalogo/importar/confirmar', datos, {
      aplicar_stock_inicial: opciones.aplicarStockInicial,
      almacen_id: opciones.almacenId ?? undefined,
    });
  },
};

export const sistemaApi = {
  /** El endpoint de salud vive fuera del prefijo `/api/v1` y no requiere token. */
  salud: () => consultarSalud(),
};
