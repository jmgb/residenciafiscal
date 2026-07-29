/**
 * Gate determinista de marca (spec: docs/superpowers/specs/2026-07-29-marca-y-brandbook-design.md §9).
 *
 * Cuatro reglas:
 *  1. Contraste: los pares permitidos de la tabla del brandbook se recalculan
 *     leyendo index.css y fallan si bajan de AA. Los pares que hoy NO cumplen
 *     se afirman al revés (siguen por debajo), para que arreglarlos obligue a
 *     actualizar la regla en lugar de dejarla caducada.
 *  2. Ningún HEX literal fuera de la fuente única (index.css) salvo las
 *     excepciones declaradas (favicon.svg, logo.svg, og-image.html).
 *  3. Nada de clases de escala sobre tokens planos: solo `primary` tiene
 *     escala 50…950; `bg-warning-50` se renderiza transparente sin avisar.
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

const SRC_FILES = walk(join(FRONTEND_ROOT, 'src')).filter((f) => /\.(ts|tsx|css)$/.test(f));

// --- Tokens ---

function token(name: string): string {
  const match = INDEX_CSS.match(new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`Token --color-${name} no encontrado en index.css`);
  return match[1];
}

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

describe('contraste de la tabla del brandbook', () => {
  const AA = 4.5;

  const pares: [string, string, string][] = [
    ['foreground', 'background', 'libre'],
    ['foreground', 'muted', 'libre'],
    ['secondary-foreground', 'secondary', 'libre'],
    ['primary', 'background', 'libre'],
    ['primary-foreground', 'primary', 'libre'],
    ['primary', 'accent', 'libre'],
    ['accent-foreground', 'accent', 'bloque de aviso'],
    ['destructive', 'background', 'libre'],
    ['success', 'background', 'libre'],
    ['warning', 'background', 'libre'],
    ['accent-600', 'background', 'libre'],
    ['muted-foreground', 'background', 'texto secundario sobre blanco'],
  ];

  it.each(pares)('%s sobre %s cumple AA (%s)', (fg, bg) => {
    expect(ratio(token(fg), token(bg))).toBeGreaterThanOrEqual(AA);
  });

  it('accent-400 sobre primary cumple AA para texto grande (isotipo)', () => {
    expect(ratio(token('accent-400'), token('primary'))).toBeGreaterThanOrEqual(3);
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
    for (const file of SRC_FILES) {
      const content = readFileSync(file, 'utf-8');
      for (const attr of content.matchAll(/className=(?:'([^']*)'|"([^"]*)"|\{`([^`]*)`\})/g)) {
        const classes = attr[1] ?? attr[2] ?? attr[3] ?? '';
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

  it('og-image.html usa placeholders inyectados, no HEX de diseño propios', () => {
    const og = readFileSync(join(FRONTEND_ROOT, 'og', 'og-image.html'), 'utf-8');
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
  });
});

// --- Clases de escala sobre tokens planos ---

describe('escalas de color', () => {
  it('solo primary lleva sufijo de escala en las clases de src/', () => {
    const offenders: string[] = [];
    const scaleClass =
      /(?:^|[\s'"`])(?:bg|text|border|ring|from|to|via)-([a-z-]+)-(\d{2,3})(?:\/\d+)?(?=$|[\s'"`])/g;
    for (const file of SRC_FILES) {
      const content = readFileSync(file, 'utf-8');
      for (const match of content.matchAll(scaleClass)) {
        const [full, base] = match;
        if (base !== 'primary' && base !== 'accent') {
          offenders.push(`${relative(FRONTEND_ROOT, file)}: ${full.trim()}`);
        }
        if (base === 'accent' && !['400', '500', '600'].includes(match[2])) {
          offenders.push(
            `${relative(FRONTEND_ROOT, file)}: ${full.trim()} (accent solo tiene 400/500/600)`
          );
        }
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
