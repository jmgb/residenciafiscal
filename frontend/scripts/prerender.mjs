#!/usr/bin/env node
/**
 * Prerenderiza las rutas públicas estáticas de la SPA a partir de `dist/index.html`.
 *
 * Los bots sociales no ejecutan JavaScript: al compartir `/manifiesto` o
 * `/metodologia` leen los metadatos de la shell, que son los de la home. Aquí se
 * escribe una copia de la shell por ruta (`dist/<ruta>/index.html`) con su título,
 * descripción, canonical e imagen OG propios. El rewrite `/* → /index.html` de
 * Netlify no está forzado, así que el archivo físico gana y esas URLs sirven la
 * copia correcta; la SPA se hidrata igual porque el bundle es el mismo.
 *
 * Se ejecuta en `postbuild`, después de `vite build`.
 *
 * Falla ruidosamente si algún patrón no encuentra exactamente una coincidencia:
 * un metadato que deja de sustituirse en silencio es peor que un build roto.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..');
const distDir = join(frontendDir, 'dist');
const shellFile = join(distDir, 'index.html');
const publicDir = join(frontendDir, 'public');

const SITE_URL = 'https://residenciafiscal.org';

/** Rutas a prerenderizar. `image` a `null` hereda la imagen OG de la home. */
const ROUTES = [
  {
    dir: 'manifiesto',
    title: 'Manifiesto — Residencia Fiscal',
    description:
      'Naciste en un país. No le perteneces. Elegir dónde vives — y dónde tributas — es un derecho. La jurisprudencia que decide estos casos, al alcance de cualquiera, siempre dentro de la ley.',
    url: `${SITE_URL}/manifiesto`,
    image: `${SITE_URL}/og-image-manifiesto.png`,
  },
  {
    dir: 'metodologia',
    title: 'Metodología — Residencia Fiscal',
    description:
      'Cómo se construyó el análisis: 106 sentencias del Tribunal Supremo y la Audiencia Nacional (2015–2025), con criterios, pruebas y fallo extraídos de forma estructurada y cita literal verificable.',
    url: `${SITE_URL}/metodologia`,
    image: null,
  },
];

/**
 * Patrones de los metadatos de la shell. Tolerantes al salto de línea porque
 * Prettier parte los `<meta>` largos en varias líneas y vite los respeta.
 */
const PATTERNS = {
  title: /<title>[\s\S]*?<\/title>/g,
  description: /<meta\s+name="description"\s+content="[\s\S]*?"\s*\/>/g,
  canonical: /<link\s+rel="canonical"\s+href="[^"]*"\s*\/>/g,
  ogTitle: /<meta\s+property="og:title"\s+content="[\s\S]*?"\s*\/>/g,
  ogDescription: /<meta\s+property="og:description"\s+content="[\s\S]*?"\s*\/>/g,
  ogUrl: /<meta\s+property="og:url"\s+content="[^"]*"\s*\/>/g,
  ogImage: /<meta\s+property="og:image"\s+content="[^"]*"\s*\/>/g,
  twitterTitle: /<meta\s+name="twitter:title"\s+content="[\s\S]*?"\s*\/>/g,
  twitterDescription: /<meta\s+name="twitter:description"\s+content="[\s\S]*?"\s*\/>/g,
  twitterImage: /<meta\s+name="twitter:image"\s+content="[^"]*"\s*\/>/g,
};

function escapeAttr(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Sustituye una coincidencia única; lanza si hay cero o más de una. */
function replaceOnce(html, label, pattern, replacement) {
  const found = html.match(pattern);
  if (found?.length !== 1) {
    throw new Error(
      `patrón "${label}": ${found?.length ?? 0} coincidencias en dist/index.html, se esperaba 1. ` +
        'Si has cambiado los metadatos de index.html, actualiza scripts/prerender.mjs.'
    );
  }
  // Reemplazo como función para que `$&` y similares no se interpreten.
  return html.replace(pattern, () => replacement);
}

function renderRoute(shell, route) {
  const title = escapeAttr(route.title);
  const description = escapeAttr(route.description);
  const url = escapeAttr(route.url);

  let html = shell;
  html = replaceOnce(html, 'title', PATTERNS.title, `<title>${title}</title>`);
  html = replaceOnce(
    html,
    'meta description',
    PATTERNS.description,
    `<meta name="description" content="${description}" />`
  );
  html = replaceOnce(
    html,
    'canonical',
    PATTERNS.canonical,
    `<link rel="canonical" href="${url}" />`
  );
  html = replaceOnce(
    html,
    'og:title',
    PATTERNS.ogTitle,
    `<meta property="og:title" content="${title}" />`
  );
  html = replaceOnce(
    html,
    'og:description',
    PATTERNS.ogDescription,
    `<meta property="og:description" content="${description}" />`
  );
  html = replaceOnce(html, 'og:url', PATTERNS.ogUrl, `<meta property="og:url" content="${url}" />`);
  html = replaceOnce(
    html,
    'twitter:title',
    PATTERNS.twitterTitle,
    `<meta name="twitter:title" content="${title}" />`
  );
  html = replaceOnce(
    html,
    'twitter:description',
    PATTERNS.twitterDescription,
    `<meta name="twitter:description" content="${description}" />`
  );

  if (route.image) {
    const image = escapeAttr(route.image);
    html = replaceOnce(
      html,
      'og:image',
      PATTERNS.ogImage,
      `<meta property="og:image" content="${image}" />`
    );
    html = replaceOnce(
      html,
      'twitter:image',
      PATTERNS.twitterImage,
      `<meta name="twitter:image" content="${image}" />`
    );
    warnIfImageMissing(route.image);
  }

  return html;
}

/**
 * Aviso (no error) si la imagen OG de la ruta no está ni en dist/ ni en public/:
 * el HTML sería válido pero la tarjeta social saldría rota.
 */
function warnIfImageMissing(imageUrl) {
  const file = basename(new URL(imageUrl).pathname);
  if (existsSync(join(distDir, file)) || existsSync(join(publicDir, file))) return;
  console.warn(`[prerender] La imagen OG "${file}" no está en dist/ ni en public/.`);
}

function main() {
  if (!existsSync(shellFile)) {
    throw new Error('no existe dist/index.html. Ejecuta `npm run build` antes de prerenderizar.');
  }

  const shell = readFileSync(shellFile, 'utf8');

  for (const route of ROUTES) {
    const targetDir = join(distDir, route.dir);
    mkdirSync(targetDir, { recursive: true });
    writeFileSync(join(targetDir, 'index.html'), renderRoute(shell, route), 'utf8');
    console.log(`[prerender] dist/${route.dir}/index.html`);
  }
}

try {
  main();
} catch (error) {
  console.error(`[prerender] ${error.message}`);
  process.exit(1);
}
