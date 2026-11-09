/**
 * Claves de caché de TanStack Query.
 * Centralizarlas evitaInvalidaciones cruzadas entre pantallas.
 */

export const claves = {
  salud: ['sistema', 'salud'] as const,
  sesion: ['auth', 'yo'] as const,
  resumen: ['dashboard', 'resumen'] as const,
  productos: {
    listado: (filtros: unknown) => ['catalogo', 'productos', filtros] as const,
    detalle: (id: number) => ['catalogo', 'producto', id] as const,
    unidades: ['catalogo', 'unidades'] as const,
    categorias: ['catalogo', 'categorias'] as const,
    marcas: ['catalogo', 'marcas'] as const,
  },
  proveedores: {
    listado: (filtros: unknown) => ['proveedores', 'listado', filtros] as const,
    detalle: (id: number) => ['proveedores', 'detalle', id] as const,
    productos: (id: number) => ['proveedores', 'productos', id] as const,
  },
  existencias: (filtros: unknown) => ['inventario', 'existencias', filtros] as const,
  ficha: (id: number) => ['inventario', 'ficha', id] as const,
  radar: ['inventario', 'radar'] as const,
  ventas: {
    listado: (filtros: unknown) => ['ventas', 'listado', filtros] as const,
    detalle: (id: number) => ['ventas', 'detalle', id] as const,
  },
  abastecimientos: {
    listado: (filtros: unknown) => ['abastecimientos', 'listado', filtros] as const,
  },
  reportes: {
    ventas: (filtros: unknown) => ['reportes', 'ventas', filtros] as const,
    abastecimientos: (filtros: unknown) => ['reportes', 'abastecimientos', filtros] as const,
    costos: (filtros: unknown) => ['reportes', 'costos', filtros] as const,
    inventario: (filtros: unknown) => ['reportes', 'inventario', filtros] as const,
    margen: (filtros: unknown) => ['reportes', 'margen', filtros] as const,
  },
  admin: {
    usuarios: (filtros: unknown) => ['admin', 'usuarios', filtros] as const,
    auditoria: (filtros: unknown) => ['admin', 'auditoria', filtros] as const,
  },
};
