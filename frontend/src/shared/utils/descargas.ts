/**
 * Utilidades para descargar archivos generados por el backend (CSV, Excel).
 * Todo es local: se crea un enlace temporal y se revoca la URL del objeto.
 */

/** Guarda en disco un `Blob` con el nombre indicado. */
export function guardarArchivo(blob: Blob, nombreArchivo: string): void {
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombreArchivo;
  enlace.rel = 'noopener';
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  window.setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/** Normaliza un nombre de archivo quitando caracteres problemáticos. */
export function nombreArchivoSeguro(base: string, extension: string): string {
  const limpio = base
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  return `${limpio || 'archivo'}.${extension}`;
}

/** Nombre de archivo con la fecha del periodo: `ventas-2026-11-01-a-2026-11-30.csv`. */
export function nombreArchivoConPeriodo(
  prefijo: string,
  desde: string | null,
  hasta: string | null,
  extension: string,
): string {
  const partes = [prefijo];
  if (desde) partes.push(desde);
  if (hasta && hasta !== desde) partes.push(`a-${hasta}`);
  return nombreArchivoSeguro(partes.join('-'), extension);
}
