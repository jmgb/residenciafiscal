/**
 * Gate determinista de marca (ver docs/brand/brand-guidelines.md §8 «Gate automático»).
 *
 * Cuatro reglas:
 *  1. Contraste: los pares permitidos de la tabla del brandbook se recalculan
 *     leyendo index.css y fallan si bajan de AA o si su ratio se aleja del
 *     valor publicado en el brandbook. Los pares que hoy NO cumplen se
 *     afirman al revés (siguen por debajo), para que arreglarlos obligue a
 *     actualizar la regla en lugar de dejarla caducada.
 *  2. Ningún HEX literal fuera de la fuente única (index.css) salvo las
 *     excepciones declaradas (favicon.svg, logo.svg, og-image.html). Cubre
 *     también los .svg de src/, que es donde viven las excepciones.
 *  3. Toda clase de utilidad de color usada en src/ apunta a un token que
 *     existe en index.css. El conjunto válido se deriva parseando los
 *     `--color-*`, no de una lista escrita a mano: `bg-primary-1000` o
 *     `bg-surface` se renderizan transparentes sin avisar.
 *  4. Toda clase `control-*` referenciada en src/ existe en index.css.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const FRONTEND_ROOT = join(__dirname, '..');
const INDEX_CSS = readFileSync(join(FRONTEND_ROOT, 'src', 'index.css'), 'utf-8');

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

// Los .svg entran porque las excepciones de HEX viven ahí (src/assets/logo.svg);
// filtrarlos dejaba esa excepción como código muerto.
const SRC_FILES = walk(join(FRONTEND_ROOT, 'src')).filter((f) => /\.(ts|tsx|css|svg)$/.test(f));
// Las reglas de clases de utilidad solo miran código: un `viewBox` de SVG o una
// declaración CSS no son clases de Tailwind.
const CODE_FILES = SRC_FILES.filter((f) => /\.tsx?$/.test(f));

// --- Tokens ---

function token(name: string): string {
  const match = INDEX_CSS.match(new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`Token --color-${name} no encontrado en index.css`);
  return match[1];
}

/** Todos los `--color-<nombre>` declarados en index.css: la lista es la fuente. */
const COLOR_TOKENS = new Set([...INDEX_CSS.matchAll(/--color-([a-z0-9-]+)\s*:/g)].map((m) => m[1]));

// --- Contraste WCAG ---

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => {
    const c = Number.parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// --- Extracción de className ---

/**
 * Devuelve el contenido de cada `className` del fichero. Cubre las formas
 * literales (`'…'`, `"…"`) y también `className={…}` con llaves balanceadas,
 * para que las clases repartidas entre los argumentos de `cn(…)` se evalúen
 * juntas. En la forma con llaves se sustituyen comillas y comas por espacios:
 * lo que queda es ruido JS separado por espacios, pero cada clase conserva sus
 * delimitadores y las reglas pueden buscarla como palabra suelta.
 */
function classNameValues(content: string): string[] {
  const values: string[] = [];
  const marker = 'className=';
  let cursor = content.indexOf(marker);
  while (cursor !== -1) {
    let after = cursor + marker.length;
    const opener = content[after];
    if (opener === "'" || opener === '"') {
      const end = content.indexOf(opener, after + 1);
      if (end === -1) break;
      values.push(content.slice(after + 1, end));
      after = end + 1;
    } else if (opener === '{') {
      let depth = 0;
      let end = after;
      for (; end < content.length; end++) {
        if (content[end] === '{') depth++;
        else if (content[end] === '}' && --depth === 0) break;
      }
      values.push(content.slice(after + 1, end).replace(/['"`,]/g, ' '));
      after = end + 1;
    }
    cursor = content.indexOf(marker, after);
  }
  return values;
}

describe('contraste de la tabla del brandbook', () => {
  const AA = 4.5;

  // El cuarto elemento es el ratio publicado en docs/brand/brand-guidelines.md.
  // Fijarlo (y no solo el umbral AA) hace que una deriva de token que siga
  // cumpliendo AA también rompa el gate: la tabla del brandbook quedaría
  // desfasada y hay que actualizarla a mano.
  const pares: [string, string, string, number][] = [
    ['foreground', 'background', 'libre', 17.85],
    ['foreground', 'canvas', 'libre', 17.06],
    ['foreground', 'muted', 'libre', 16.3],
    ['secondary-foreground', 'secondary', 'libre', 13.35],
    ['primary', 'background', 'libre', 11.5],
    ['primary-foreground', 'primary', 'libre', 10.99],
    ['primary', 'accent', 'libre', 11.09],
    ['accent-foreground', 'accent', 'bloque de aviso', 8.75],
    ['destructive', 'background', 'libre', 6.47],
    ['accent-400', 'primary', 'isotipo sobre azul', 5.36],
    ['success', 'background', 'libre', 5.02],
    ['warning', 'background', 'libre', 5.02],
    ['accent-600', 'background', 'libre', 5.02],
    ['primary', 'canvas', 'libre', 10.99],
    ['muted-foreground', 'background', 'texto secundario sobre blanco', 4.76],
    ['muted-foreground', 'canvas', 'texto secundario sobre el lienzo', 4.55],
  ];

  it.each(pares)('%s sobre %s cumple AA (%s)', (fg, bg, _uso, esperado) => {
    const medido = ratio(token(fg), token(bg));
    expect(medido).toBeGreaterThanOrEqual(AA);
    expect(medido).toBeCloseTo(esperado, 1);
  });

  // Pares que hoy NO cumplen: si alguien retoca el token y los arregla, este
  // test se cae y obliga a actualizar la regla del brandbook.
  it('muted-foreground sobre muted sigue por debajo de AA (regla 1 del brandbook)', () => {
    expect(ratio(token('muted-foreground'), token('muted'))).toBeLessThan(AA);
  });

  it('accent-500 sobre blanco sigue por debajo de AA (regla 2 del brandbook)', () => {
    expect(ratio(token('accent-500'), token('background'))).toBeLessThan(AA);
  });

  it('ningún className combina fondo teñido con muted-foreground ni usa text-accent-500', () => {
    const offenders: string[] = [];
    for (const file of CODE_FILES) {
      const content = readFileSync(file, 'utf-8');
      for (const classes of classNameValues(content)) {
        const tinted = /(?:^|\s)bg-(?:muted|secondary)(?:$|\s)/.test(classes);
        if (
          (tinted && classes.includes('text-muted-foreground')) ||
          classes.includes('text-accent-500')
        ) {
          offenders.push(`${relative(FRONTEND_ROOT, file)}: ${classes}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});

// --- HEX literales ---

describe('fuente única de color', () => {
  it('ningún HEX literal en src/ fuera de index.css', () => {
    const offenders: string[] = [];
    for (const file of SRC_FILES) {
      if (file.endsWith('index.css')) continue;
      if (file.endsWith(join('assets', 'logo.svg'))) continue;
      const content = readFileSync(file, 'utf-8');
      const matches = content.match(/#[0-9a-fA-F]{6}\b/g);
      if (matches) offenders.push(`${relative(FRONTEND_ROOT, file)}: ${matches.join(', ')}`);
    }
    expect(offenders).toEqual([]);
  });

  it('las excepciones declaradas usan HEX que existen como token', () => {
    const tokens = new Set(INDEX_CSS.match(/#[0-9a-fA-F]{6}/g) ?? []);
    const exceptions = [
      join(FRONTEND_ROOT, 'public', 'favicon.svg'),
      join(FRONTEND_ROOT, 'src', 'assets', 'logo.svg'),
    ];
    for (const file of exceptions) {
      const hexes = readFileSync(file, 'utf-8').match(/#[0-9a-fA-F]{6}/g) ?? [];
      expect(hexes.length, `${file} debería declarar HEX literales`).toBeGreaterThan(0);
      for (const hex of hexes) {
        expect(
          tokens.has(hex.toLowerCase()),
          `${hex} de ${relative(FRONTEND_ROOT, file)} no es un token de index.css`
        ).toBe(true);
      }
    }
  });

  it.each(['og-image.html', 'og-image-manifiesto.html'])(
    '%s usa placeholders inyectados, no HEX de diseño propios',
    (source) => {
      const og = readFileSync(join(FRONTEND_ROOT, 'og', source), 'utf-8');
      // Los únicos HEX admisibles son los del comentario de cabecera; el CSS de
      // la pieza usa __TOKEN__ que render.sh sustituye leyendo index.css.
      const style = og.slice(og.indexOf('<style>'), og.indexOf('</style>'));
      expect(style.match(/#[0-9a-fA-F]{6}/g)).toBeNull();
      for (const placeholder of [
        '__BACKGROUND__',
        '__FOREGROUND__',
        '__PRIMARY__',
        '__MUTED_FOREGROUND__',
      ]) {
        expect(style).toContain(placeholder);
      }
    }
  );
});

// --- Clases de color contra tokens inexistentes ---

describe('escalas de color', () => {
  // Prefijos de Tailwind que resuelven un color. `ring-offset` antes que `ring`
  // para que la alternancia consuma el prefijo largo.
  const COLOR_PREFIX =
    'bg|text|border(?:-[trblxyse])?|ring-offset|ring|outline|fill|stroke|from|via|to|decoration|divide|caret|placeholder|shadow';
  // Una clase suelta: variantes opcionales (`hover:`, `dark:`, `sm:`,
  // `data-[state=open]:`), `!` de importancia, prefijo, valor y modificador de
  // opacidad opcional (`/40`).
  const COLOR_CLASS = new RegExp(
    `(?:^|[\\s'"\`])((?:[a-z0-9-]+(?:\\[[^\\]\\s]*\\])?:)*)!?(${COLOR_PREFIX})-([a-z][a-z0-9-]*)(?:/[\\d.]+)?(?=$|[\\s'"\`])`,
    'g'
  );

  // Vocabulario de Tailwind que comparte prefijo con las clases de color pero
  // no resuelve ningún token: tamaños, alineaciones, anchos, estilos de borde,
  // la paleta por defecto y los valores arbitrarios. Es la única forma de
  // distinguir `bg-white` (válido) de `bg-surface` (token inexistente, se
  // renderiza transparente). Si aparece una utilidad legítima que no esté
  // aquí, el gate se pondrá rojo: se añade a esta lista, no se relaja la regla.
  const TAILWIND_NO_COLOR = new RegExp(
    `^(?:${[
      '\\[.*\\]', // valores arbitrarios: text-[10px], bg-[--var]
      'current|inherit|transparent|white|black',
      // `inset` es la variante de `ring-`/`shadow-` que dibuja hacia dentro:
      // comparte prefijo con las clases de color pero no resuelve ningún token.
      'none|auto|full|px|inner|inset|outline',
      '(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald' +
        '|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)(?:-\\d{1,3})?',
      '[trblxyse](?:-.*)?', // direccionales de border: border-b, border-l-4
      'xs|sm|base|md|lg|\\d?xl',
      'left|center|right|justify|start|end|balance|pretty|wrap|nowrap|ellipsis|clip',
      'solid|dashed|dotted|double|hidden|collapse|separate',
      'gradient-to-.*|linear-.*|radial.*|conic.*',
      'cover|contain|fixed|local|scroll|repeat.*|no-repeat|top|bottom',
      'origin-.*|blend-.*|clip-.*|offset-.*',
    ].join('|')})$`
  );

  it('toda clase de color de src/ apunta a un token declarado en index.css', () => {
    const offenders: string[] = [];
    for (const file of CODE_FILES) {
      const content = readFileSync(file, 'utf-8');
      for (const match of content.matchAll(COLOR_CLASS)) {
        const value = match[3];
        if (COLOR_TOKENS.has(value)) continue;
        if (TAILWIND_NO_COLOR.test(value)) continue;
        const clase = match[0].trim().replace(/^['"`]/, '');
        offenders.push(`${relative(FRONTEND_ROOT, file)}: ${clase} (--color-${value} no existe)`);
      }
    }
    expect(offenders).toEqual([]);
  });
});

// --- Clases control-* ---

describe('utilidades control-*', () => {
  it('toda clase control-* referenciada existe en index.css', () => {
    const defined = new Set([...INDEX_CSS.matchAll(/\.(control-[a-z-]+)\s*\{/g)].map((m) => m[1]));
    const offenders: string[] = [];
    for (const file of SRC_FILES) {
      if (file.endsWith('.css')) continue;
      const content = readFileSync(file, 'utf-8');
      for (const match of content.matchAll(/(?:^|[\s'"`])(control-[a-z-]+)/g)) {
        if (!defined.has(match[1])) {
          offenders.push(`${relative(FRONTEND_ROOT, file)}: ${match[1]}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});
