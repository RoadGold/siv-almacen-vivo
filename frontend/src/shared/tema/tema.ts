/**
 * Tema visual (claro / oscuro / según el sistema).
 *
 * La preferencia se guarda en `localStorage` y se aplica como
 * `data-tema="oscuro"` en <html>, de modo que todas las variables CSS
 * cambian a la vez sin que ningún componente tenga que saber del tema.
 */

export type Tema = 'claro' | 'oscuro';
export type PreferenciaTema = Tema | 'sistema';

export const CLAVE_PREFERENCIA = 'siv.tema';

export const ETIQUETAS: Record<PreferenciaTema, string> = {
  claro: 'Modo claro',
  oscuro: 'Modo oscuro',
  sistema: 'Según el sistema',
};

export function preferenciaGuardada(): PreferenciaTema {
  try {
    const valor = window.localStorage.getItem(CLAVE_PREFERENCIA);
    if (valor === 'claro' || valor === 'oscuro' || valor === 'sistema') return valor;
  } catch {
    // localStorage puede estar bloqueado (modo privado): se usa el sistema.
  }
  return 'sistema';
}

export function sistemaPrefiereOscuro(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  );
}

export function resolverTema(preferencia: PreferenciaTema): Tema {
  if (preferencia === 'sistema') return sistemaPrefiereOscuro() ? 'oscuro' : 'claro';
  return preferencia;
}

/** Aplica el tema al documento. Debe llamarse también antes de pintar la app. */
export function aplicarTema(tema: Tema): void {
  const raiz = document.documentElement;
  raiz.dataset.tema = tema;
  raiz.style.colorScheme = tema;
}

export function guardarPreferencia(preferencia: PreferenciaTema): void {
  try {
    window.localStorage.setItem(CLAVE_PREFERENCIA, preferencia);
  } catch {
    // Sin persistencia: el tema funciona igual durante la sesión.
  }
}
