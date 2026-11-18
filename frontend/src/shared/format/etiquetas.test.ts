/**
 * Verificación automática de las etiquetas y los ejemplos de los campos de entrada.
 *
 * Regla del sistema: en CADA campo de entrada se debe ver el NOMBRE del dato que
 * se rellena (etiqueta visible, no solo para lectores de pantalla) y un EJEMPLO
 * de lo que se debe escribir (placeholder dentro del cuadro).
 *
 * La prueba recorre los `.tsx` de `src/features` con el analizador de TypeScript
 * y falla si encuentra:
 *   - un `<Input>` o `<Textarea>` sin ejemplo (ni como `ejemplo` del `<Field>`
 *     que lo envuelve, ni como `placeholder` propio),
 *   - una etiqueta `sr-only` en un campo de entrada,
 *   - un `<Field>` sin `etiqueta`,
 *   - un `<Input>` o `<Textarea>` sin etiqueta visible asociada.
 *
 * La revisión alcanza TODAS las pantallas del sistema, incluidas las
 * estaciones VENDER y RECIBIR: la regla es que ningún campo de entrada se
 * queda sin el nombre visible del dato y sin un ejemplo de lo que se escribe.
 */
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';
import ts from 'typescript';

const aqui = dirname(fileURLToPath(import.meta.url));
const raizFeatures = join(aqui, '..', '..', 'features');

/**
 * Carpetas excluidas de la revisión.
 * Vacío: la regla se aplica a todas las pantallas, sin excepciones.
 */
const CARPETAS_EXCLUIDAS: string[] = [];

export interface Problema {
  /** Ruta del archivo relativa a `src/features`. */
  archivo: string;
  /** Línea 1-based dentro del archivo. */
  linea: number;
  /** Qué está mal y cómo se corrige. */
  mensaje: string;
}

/** Lista recursiva de los `.tsx` que hay que revisar. */
export function archivosParaRevisar(directorio: string = raizFeatures): string[] {
  const encontrados: string[] = [];
  for (const entrada of readdirSync(directorio)) {
    const ruta = join(directorio, entrada);
    if (statSync(ruta).isDirectory()) {
      if (CARPETAS_EXCLUIDAS.includes(entrada)) continue;
      encontrados.push(...archivosParaRevisar(ruta));
    } else if (ruta.endsWith('.tsx')) {
      encontrados.push(ruta);
    }
  }
  return encontrados;
}

/** Nombre del componente JSX (`Input`, `Textarea`, `Field`…). */
function nombreTag(nodo: ts.Node): string {
  if (ts.isJsxElement(nodo)) return nodo.openingElement.tagName.getText();
  if (ts.isJsxSelfClosingElement(nodo)) return nodo.tagName.getText();
  return '';
}

/** Etiqueta de apertura de un elemento JSX. */
function apertura(
  nodo: ts.JsxElement | ts.JsxSelfClosingElement,
): ts.JsxOpeningElement | ts.JsxSelfClosingElement {
  return ts.isJsxElement(nodo) ? nodo.openingElement : nodo;
}

/** Nombre de un atributo JSX (`className`, `htmlFor`…). */
function nombreAtributo(atributo: ts.JsxAttribute): string {
  return ts.isIdentifier(atributo.name) ? atributo.name.text : atributo.name.getText();
}

/** Busca un atributo JSX por nombre. */
function atributo(
  nodo: ts.JsxElement | ts.JsxSelfClosingElement,
  nombre: string,
): ts.JsxAttribute | undefined {
  return apertura(nodo).attributes.properties.find(
    (propiedad): propiedad is ts.JsxAttribute =>
      ts.isJsxAttribute(propiedad) && nombreAtributo(propiedad) === nombre,
  );
}

/** Valor textual de un atributo (solo literales). */
function valorAtributo(atributo: ts.JsxAttribute | undefined): string | undefined {
  if (!atributo?.initializer) return undefined;
  const inicializador = atributo.initializer;
  return ts.isStringLiteral(inicializador) ? inicializador.text : undefined;
}

/**
 * Tipos de campo en los que el navegador ya muestra el formato de la fecha
 * (dd/mm/aaaa): ahí no cabe un placeholder y basta la etiqueta visible con su
 * texto de ayuda.
 */
const TIPOS_CON_FORMATO_PROPIO = ['date', 'datetime-local', 'month', 'week', 'time', 'file'];

/** Revisa un archivo y devuelve los problemas encontrados. */
export function revisarArchivo(contenido: string, nombreArchivo: string): Problema[] {
  const problemas: Problema[] = [];
  const fuente = ts.createSourceFile(
    nombreArchivo,
    contenido,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );

  function anotar(nodo: ts.Node, mensaje: string) {
    const posicion = fuente.getLineAndCharacterOfPosition(nodo.getStart());
    problemas.push({ archivo: nombreArchivo, linea: posicion.line + 1, mensaje });
  }

  /**
   * Identificadores con etiqueta visible: los `htmlFor` de los `<label>` y de
   * los `<Field>` (el `Field` dibuja una etiqueta visible con `for`).
   */
  const conEtiquetaVisible = new Set<string>();

  function recorrer(nodo: ts.Node, ancestros: ts.Node[]) {
    if (ts.isJsxAttribute(nodo) && nombreAtributo(nodo) === 'className') {
      const texto = nodo.initializer?.getText() ?? '';
      if (texto.includes('sr-only')) {
        anotar(
          nodo,
          'se usa la clase «sr-only»: el nombre del dato debe verse en pantalla, no solo para lectores de pantalla.',
        );
      }
    }

    if (ts.isJsxElement(nodo) || ts.isJsxSelfClosingElement(nodo)) {
      const nombre = nombreTag(nodo);

      if (nombre === 'label' || nombre === 'Field') {
        const htmlFor = valorAtributo(atributo(nodo, 'htmlFor'));
        if (htmlFor) conEtiquetaVisible.add(htmlFor);
      }

      if (nombre === 'Field' && !atributo(nodo, 'etiqueta')) {
        anotar(nodo, 'el <Field> no declara «etiqueta»: falta el nombre visible del dato.');
      }

      if (nombre === 'Input' || nombre === 'Textarea') {
        const ejemploPropio = atributo(nodo, 'placeholder');
        const campo = ancestros
          .slice()
          .reverse()
          .find(
            (ancestro): ancestro is ts.JsxElement =>
              ts.isJsxElement(ancestro) && nombreTag(ancestro) === 'Field',
          );
        const ejemploDelField = campo ? atributo(campo, 'ejemplo') : undefined;
        const tipo = valorAtributo(atributo(nodo, 'type'));

        // En las fechas el navegador ya muestra dd/mm/aaaa: no admiten ejemplo.
        if (!ejemploPropio && !ejemploDelField && !TIPOS_CON_FORMATO_PROPIO.includes(tipo ?? '')) {
          anotar(
            nodo,
            `<${nombre}> sin ejemplo: pon «ejemplo» en el <Field> que lo envuelve o «placeholder» en el control.`,
          );
        }

        const id = valorAtributo(atributo(nodo, 'id'));
        const tieneEtiqueta = Boolean(campo) || (id !== undefined && conEtiquetaVisible.has(id));
        if (!tieneEtiqueta) {
          anotar(
            nodo,
            `<${nombre}> sin etiqueta visible: envuélvelo en un <Field etiqueta="…"> o asociá un <label htmlFor="${id ?? 'id'}">.`,
          );
        }
      }
    }

    ts.forEachChild(nodo, (hijo) => recorrer(hijo, [...ancestros, nodo]));
  }

  recorrer(fuente, []);
  return problemas;
}

const ARCHIVOS = archivosParaRevisar();
const PROBLEMAS: Problema[] = ARCHIVOS.flatMap((ruta) =>
  revisarArchivo(readFileSync(ruta, 'utf8'), relative(raizFeatures, ruta).replace(/\\/g, '/')),
);

describe('etiquetas y ejemplos de los campos de entrada', () => {
  it('se encontraron archivos que revisar', () => {
    expect(ARCHIVOS.length).toBeGreaterThan(0);
  });

  it('cada campo de entrada tiene nombre visible y ejemplo', () => {
    const detalle = PROBLEMAS.map(
      (problema) => `  ${problema.archivo}:${problema.linea} — ${problema.mensaje}`,
    ).join('\n');
    expect(
      PROBLEMAS,
      `Hay ${PROBLEMAS.length} campo(s) sin etiqueta visible o sin ejemplo:\n${detalle}`,
    ).toEqual([]);
  });
});

/**
 * La revisión se prueba con casos sintéticos: si el analizador dejara pasar
 * un campo sin ejemplo o sin etiqueta, la prueba de arriba no serviría de nada.
 */
describe('la revisión detecta los errores que debe detectar', () => {
  it('detecta un campo sin ejemplo', () => {
    const problemas = revisarArchivo(
      '<Field htmlFor="x" etiqueta="Cantidad"><Input id="x" /></Field>',
      'caso.tsx',
    );
    expect(problemas.some((problema) => problema.mensaje.includes('sin ejemplo'))).toBe(true);
  });

  it('detecta un <Field> sin etiqueta', () => {
    const problemas = revisarArchivo(
      '<Field htmlFor="x"><Input id="x" placeholder="10" /></Field>',
      'caso.tsx',
    );
    expect(problemas.some((problema) => problema.mensaje.includes('«etiqueta»'))).toBe(true);
  });

  it('detecta una etiqueta «sr-only»', () => {
    const problemas = revisarArchivo(
      '<label htmlFor="x" className="sr-only">Cantidad</label><Input id="x" placeholder="10" />',
      'caso.tsx',
    );
    expect(problemas.some((problema) => problema.mensaje.includes('sr-only'))).toBe(true);
  });

  it('detecta un campo sin etiqueta visible', () => {
    const problemas = revisarArchivo('<Input id="x" placeholder="10" />', 'caso.tsx');
    expect(problemas.some((problema) => problema.mensaje.includes('sin etiqueta visible'))).toBe(
      true,
    );
  });

  it('acepta un campo correcto', () => {
    const problemas = revisarArchivo(
      '<Field htmlFor="x" etiqueta="Cantidad" ejemplo="10"><Input id="x" /></Field>',
      'caso.tsx',
    );
    expect(problemas).toEqual([]);
  });

  it('acepta un campo de fecha sin ejemplo (el navegador muestra dd/mm/aaaa)', () => {
    const problemas = revisarArchivo(
      '<Field htmlFor="x" etiqueta="Desde"><Input id="x" type="date" /></Field>',
      'caso.tsx',
    );
    expect(problemas).toEqual([]);
  });
});
