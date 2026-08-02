#!/usr/bin/env node
/**
 * Inyecta en `dist/index.html` el `preload` de las tipografías autoalojadas.
 *
 * Desde que Space Grotesk e Inter se sirven desde el mismo origen
 * (`@fontsource-variable/*`, importados en `src/main.tsx`), el navegador ya no
 * abre dos conexiones a Google Fonts. Pero sigue descubriéndolas tarde: primero
 * baja el CSS del bundle y solo al aplicarlo pide el woff2, un viaje de ida y
 * vuelta extra justo delante del texto que mide el LCP. El `preload` lo empieza
 * a la vez que el CSS.
 *
 * No puede escribirse a mano en `index.html` porque vite emite los woff2 con
 * hash de contenido en el nombre; aquí se leen del CSS ya emitido.
 *
 * Solo se precargan los subconjuntos `latin`, que son los que cubre el
 * castellano de todas las páginas. `latin-ext`, `cyrillic`, `greek` y
 * `vietnamese` viajan igualmente en el deploy, pero su `unicode-range` los deja
 * sin pedir salvo que algún carácter los necesite; precargarlos sería gastar
 * datos del móvil en fuentes que nadie pinta.
 *
 * Se ejecuta en el `postbuild` **antes** de `prerender.mjs`, para que las
 * copias por ruta hereden las mismas etiquetas.
 *
 * Falla ruidosamente si un woff2 esperado no aparece exactamente una vez: un
 * `preload` a un fichero inexistente cuesta un 404 y una advertencia en
 * consola, y uno que desaparece en silencio devuelve el viaje extra sin que
 * nadie se entere.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** Nombre de fichero (sin hash) de cada subconjunto latino a precargar. */
const PRELOADED_FONTS = ['inter-latin-wght-normal', 'space-grotesk-latin-wght-normal'];

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(scriptDir, '..');
const distDir = resolve(frontendDir, process.argv[2] ?? 'dist');
const shellFile = join(distDir, 'index.html');

const html = readFileSync(shellFile, 'utf8');

/** Hojas de estilo emitidas por vite, tal como las enlaza la shell. */
const stylesheets = (html.match(/<link\b[^>]*rel="stylesheet"[^>]*>/g) ?? [])
  .map((link) => link.match(/href="([^"]+)"/)?.[1])
  .filter((href) => typeof href === 'string' && href.endsWith('.css'));

if (stylesheets.length === 0) {
  throw new Error(`[font-preload] ${shellFile} no enlaza ninguna hoja de estilo`);
}

const css = stylesheets
  .map((href) => readFileSync(join(distDir, href.replace(/^\//, '')), 'utf8'))
  .join('\n');

const emittedFonts = [...css.matchAll(/url\(\s*["']?([^"')]+\.woff2)["']?\s*\)/g)].map(
  (match) => match[1]
);

const fontUrls = PRELOADED_FONTS.map((font) => {
  const matches = [...new Set(emittedFonts.filter((url) => basename(url).startsWith(`${font}-`)))];
  if (matches.length !== 1) {
    throw new Error(
      `[font-preload] Se esperaba una única URL para "${font}" en el CSS emitido; encontradas ${matches.length}: ${matches.join(', ')}`
    );
  }
  return matches[0];
});

if (!html.includes('</head>')) {
  throw new Error(`[font-preload] ${shellFile} no tiene </head>`);
}

// `crossorigin` es obligatorio aunque la fuente sea del mismo origen: sin él el
// navegador descarga el woff2 dos veces, porque el `preload` y la petición que
// hace el CSS usan modos de CORS distintos y no comparten entrada de caché.
const tags = fontUrls
  .map((url) => `    <link rel="preload" as="font" type="font/woff2" href="${url}" crossorigin />`)
  .join('\n');

writeFileSync(shellFile, html.replace('</head>', `${tags}\n  </head>`), 'utf8');
console.log(`[font-preload] ${fontUrls.length} fuentes precargadas en ${shellFile}`);
