#!/usr/bin/env node
/**
 * Prerenderiza las rutas públicas de la SPA a partir de `dist/index.html`.
 *
 * Dos cosas, y las dos porque los bots no ejecutan JavaScript:
 *
 * 1. **Metadatos por ruta.** Al compartir `/manifiesto` o `/francia`, un bot
 *    social leía los de la shell, que son los de la home. Aquí se escribe una
 *    copia por ruta (`dist/<ruta>/index.html`) con su título, descripción,
 *    canonical e imagen OG propios.
 * 2. **Contenido.** El HTML servido era `<div id="root"></div>`: sin JavaScript
 *    no había una sola línea de texto, así que un buscador que no ejecute el
 *    bundle —o que lo posponga— indexaba páginas vacías. Ahora cada copia lleva
 *    la página ya renderizada por `dist-ssr/entry-server.js`.
 *
 * Cada ruta prerenderizada se sirve desde su fichero físico (las de país por
 * las reglas `200!` de `_redirects`, las estáticas por las de `netlify.toml`);
 * el fallback `/*` devuelve `404.html` con 404, así que una ruta sin copia
 * prerenderizada ni regla propia deja de existir para el navegador. En el
 * navegador se monta la misma aplicación de siempre sobre ese HTML.
 *
 * Se ejecuta en `postbuild`, después de `vite build` y del build SSR.
 *
 * Falla ruidosamente si algún patrón no encuentra exactamente una coincidencia
 * o si una ruta no renderiza: una página que deja de tener contenido en
 * silencio es peor que un build roto.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  esBorrador,
  fichaDescription,
  fichaPath,
  fichaTitle,
  NORMATIVA_INDEX_PATH,
  PRECEPTO_PRELOAD_ELEMENT_ID,
  render,
  SENTENCIA_PRELOAD_ELEMENT_ID,
  SENTENCIAS_INDEX_PATH,
  sentenciaDescription,
  sentenciaPath,
  sentenciaTitle,
  TREATY_PRELOAD_ELEMENT_ID,
} from '../dist-ssr/entry-server.js';
import countryRoutes from '../src/data/countryRoutes.json' with { type: 'json' };
import staticRoutes from '../src/data/staticRoutes.json' with { type: 'json' };
import treatyRelations from '../src/data/treatyRelations.json' with { type: 'json' };

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..');
const distDir = join(frontendDir, 'dist');
const shellFile = join(distDir, 'index.html');
const publicDir = join(frontendDir, 'public');

const SITE_URL = 'https://residenciafiscal.org';

/** Índice normativo ya generado por `build-normativa.mjs` en el `prebuild`. */
const NORMATIVA = JSON.parse(readFileSync(join(publicDir, 'data', 'normativa.json'), 'utf8'));

/**
 * Sentencias que `build-sentencias.mjs` ha materializado en este build. En un
 * build público son solo las `published` —hoy, ninguna—; con
 * `SENTENCIAS_PREVIEW=1` entran también los borradores internos, y entonces
 * cada ficha se emite con `noindex` porque su estado sigue siendo
 * `internal_preview`.
 *
 * Ni el índice ni las fichas se prerenderizan si no hay ninguna sentencia
 * materializada: un listado vacío sería una URL indexable sin contenido propio,
 * y sin fichero el fallback de Netlify devuelve un 404 real.
 */
const SENTENCIAS_INDEX_FILE = join(publicDir, 'data', 'sentencias.json');
const SENTENCIAS = existsSync(SENTENCIAS_INDEX_FILE)
  ? JSON.parse(readFileSync(SENTENCIAS_INDEX_FILE, 'utf8'))
  : { judgments: [] };

/** Rutas a prerenderizar. `image` a `null` hereda la imagen OG de la home. */
/** Convenio vigente de una jurisdicción, desde el registro bilateral. */
function currentTreatyBoeId(code) {
  const instruments = treatyRelations.byCounterpart[code] ?? [];
  return instruments.find((instrument) => instrument.status === 'current')?.boeId ?? null;
}

const COUNTRY_ROUTES = countryRoutes.map((route) => ({
  path: route.path,
  treatyBoeId: currentTreatyBoeId(route.code),
  dir: route.path.slice(1),
  // El título sale del JSON y no se compone aquí, por el mismo motivo que en las
  // rutas estáticas: la página lo fija también en runtime y dos copias divergen.
  title: route.title,
  description: route.description,
  robots: route.indexable ? 'index, follow' : 'noindex, follow',
  url: `${SITE_URL}${route.path}`,
  image: null,
}));

/**
 * Rutas que no son de país. Los metadatos salen de `staticRoutes.json` y no de
 * aquí: la página los fija también en runtime, y con dos copias el visitante y
 * el bot podían leer descripciones distintas sin que nada lo detectara.
 */
const STATIC_ROUTES = staticRoutes.map((route) => ({
  path: route.path,
  treatyBoeId: null,
  dir: route.path.slice(1),
  title: route.title,
  description: route.description,
  robots: route.indexable ? 'index, follow' : 'noindex, follow',
  url: `${SITE_URL}${route.path}`,
  image: route.image ? `${SITE_URL}${route.image}` : null,
}));

/**
 * Fichas de precepto: una por artículo del corpus normativo. El título y la
 * descripción salen de `normativa-fichas.ts` a través del bundle SSR, que es
 * exactamente lo que fija la página en runtime.
 */
const PRECEPTO_ROUTES = NORMATIVA.map((entry) => ({
  path: fichaPath(entry),
  treatyBoeId: null,
  preceptoSlug: entry.slug,
  dir: fichaPath(entry).slice(1),
  title: fichaTitle(entry),
  description: fichaDescription(entry),
  robots: 'index, follow',
  url: `${SITE_URL}${fichaPath(entry)}`,
  image: null,
}));

/** Una ruta por ficha de sentencia materializada, más su índice. */
const SENTENCIA_ROUTES =
  SENTENCIAS.judgments.length === 0
    ? []
    : [
        {
          path: SENTENCIAS_INDEX_PATH,
          treatyBoeId: null,
          sentenciasIndex: true,
          dir: SENTENCIAS_INDEX_PATH.slice(1),
          title: 'Sentencias sobre residencia fiscal en España: fichas por sentencia',
          description:
            'Fichas de las sentencias del Tribunal Supremo y la Audiencia Nacional sobre ' +
            'residencia fiscal: criterios aplicados, pruebas valoradas, resultado y extractos ' +
            'literales con su página.',
          // El índice solo es indexable si todas sus fichas lo son: enlazar
          // borradores desde una página indexable los expondría igualmente.
          robots: SENTENCIAS.judgments.every((entry) => !esBorrador(entry))
            ? 'index, follow'
            : 'noindex, follow',
          url: `${SITE_URL}${SENTENCIAS_INDEX_PATH}`,
          image: null,
        },
        ...SENTENCIAS.judgments.map((entry) => ({
          path: sentenciaPath(entry.judgmentId),
          treatyBoeId: null,
          judgmentId: entry.judgmentId,
          dir: sentenciaPath(entry.judgmentId).slice(1),
          title: sentenciaTitle(entry),
          description: sentenciaDescription(entry),
          robots: esBorrador(entry) ? 'noindex, follow' : 'index, follow',
          url: `${SITE_URL}${sentenciaPath(entry.judgmentId)}`,
          image: null,
        })),
      ];

const ROUTES = [...COUNTRY_ROUTES, ...STATIC_ROUTES, ...PRECEPTO_ROUTES, ...SENTENCIA_ROUTES];

/**
 * Patrones de los metadatos de la shell. Tolerantes al salto de línea porque
 * Prettier parte los `<meta>` largos en varias líneas y vite los respeta.
 */
const PATTERNS = {
  root: /<div id="root"><\/div>/g,
  title: /<title>[\s\S]*?<\/title>/g,
  description: /<meta\s+name="description"\s+content="[\s\S]*?"\s*\/>/g,
  robots: /<meta\s+name="robots"\s+content="[\s\S]*?"\s*\/>/g,
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

/**
 * Convenios que la página necesita resueltos antes de renderizarse.
 *
 * `TaxTreaty` los pide por `fetch` en un efecto, y en el build no hay efectos:
 * sin sembrarlos, el HTML estático diría «Cargando el convenio…», que es
 * justamente lo que este script existe para evitar.
 */
function preloadTreaties(route) {
  if (!route.treatyBoeId) return {};
  const entry = NORMATIVA.find((precepto) => precepto.boeId === route.treatyBoeId);
  if (!entry) {
    throw new Error(
      `${route.path}: el convenio ${route.treatyBoeId} no está en public/data/normativa.json. ` +
        'Regenera el corpus con `make export-normativa` y `node scripts/build-normativa.mjs`.'
    );
  }
  const preceptoFile = join(publicDir, 'data', 'preceptos', `${entry.slug}.json`);
  const texto = existsSync(preceptoFile) ? JSON.parse(readFileSync(preceptoFile, 'utf8')) : null;
  return { [entry.boeId]: { entry, texto } };
}

/**
 * JSON embebible en la página. `<` escapado porque un `</script>` dentro del
 * texto legal cerraría la etiqueta y rompería el documento.
 */
function embedJson(value) {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

/**
 * Preceptos que la ruta necesita resueltos antes de renderizarse, por el mismo
 * motivo que los convenios: la página los pide por `fetch` en un efecto y en el
 * build no hay efectos.
 *
 * - La ficha (`preceptoSlug`) lleva su entrada y su articulado literal.
 * - El índice (`NORMATIVA_INDEX_PATH`) lleva las 110 entradas sin las citas de
 *   sentencias: la lista solo pinta título y estado, y embeber también las
 *   citas doblaría el peso de ese HTML sin cambiar un píxel.
 */
function preloadPreceptos(route) {
  if (route.preceptoSlug) {
    const entry = NORMATIVA.find((precepto) => precepto.slug === route.preceptoSlug);
    if (!entry) {
      throw new Error(`${route.path}: el precepto no está en public/data/normativa.json.`);
    }
    const preceptoFile = join(publicDir, 'data', 'preceptos', `${entry.slug}.json`);
    if (!existsSync(preceptoFile)) {
      throw new Error(
        `${route.path}: falta public/data/preceptos/${entry.slug}.json. ` +
          'Regenera el corpus con `node scripts/build-normativa.mjs`.'
      );
    }
    const texto = JSON.parse(readFileSync(preceptoFile, 'utf8'));
    return { [entry.slug]: { entry, texto } };
  }
  if (route.path === NORMATIVA_INDEX_PATH) {
    return Object.fromEntries(
      NORMATIVA.map((entry) => [entry.slug, { entry: { ...entry, sentencias: [] }, texto: null }])
    );
  }
  // La ficha de una sentencia enlaza el artículo de residencia del convenio que
  // regía sus ejercicios, y resuelve el slug por `boeId` porque el BOE no lo
  // numera igual en todos (`a4`, `ar-4`, `ai-4`, `a1-5`). Sin sembrarlo aquí,
  // ese enlace solo aparecería después de ejecutar JavaScript, y es de los que
  // Google debe poder seguir en el HTML.
  if (route.judgmentId) {
    const ficha = JSON.parse(
      readFileSync(join(publicDir, 'data', 'sentencias', `${route.judgmentId}.json`), 'utf8')
    );
    const identificadores = new Set(
      ficha.jurisdictions.flatMap((jurisdiccion) => jurisdiccion.treatyBoeIds ?? [])
    );
    return Object.fromEntries(
      NORMATIVA.filter((entry) => identificadores.has(entry.boeId)).map((entry) => [
        entry.slug,
        { entry: { ...entry, sentencias: [] }, texto: null },
      ])
    );
  }
  return {};
}

/**
 * Sentencias resueltas antes de renderizar, por el mismo motivo que los
 * preceptos: en el build no corren los efectos y la ficha saldría diciendo
 * «Cargando la sentencia…».
 */
function preloadSentencias(route) {
  if (route.judgmentId) {
    const fichaFile = join(publicDir, 'data', 'sentencias', `${route.judgmentId}.json`);
    if (!existsSync(fichaFile)) {
      throw new Error(
        `${route.path}: falta public/data/sentencias/${route.judgmentId}.json. ` +
          'Regenera con `node scripts/build-sentencias.mjs`.'
      );
    }
    return {
      index: null,
      fichas: { [route.judgmentId]: JSON.parse(readFileSync(fichaFile, 'utf8')) },
    };
  }
  if (route.sentenciasIndex) return { index: SENTENCIAS, fichas: {} };
  return { index: null, fichas: {} };
}

function renderRoute(shell, route) {
  const title = escapeAttr(route.title);
  const description = escapeAttr(route.description);
  const url = escapeAttr(route.url);
  const treaties = preloadTreaties(route);
  const preceptos = preloadPreceptos(route);
  const sentencias = preloadSentencias(route);
  const haySentencias = sentencias.index !== null || Object.keys(sentencias.fichas).length > 0;

  let html = shell;
  // El contenido va dentro de `#root`, no en un `<noscript>`: es la misma
  // página que verá quien sí ejecute JavaScript, no una versión aparte.
  html = replaceOnce(
    html,
    'div#root',
    PATTERNS.root,
    `<div id="root">${render(route.path, treaties, preceptos, sentencias)}</div>` +
      (Object.keys(treaties).length > 0
        ? `<script id="${TREATY_PRELOAD_ELEMENT_ID}" type="application/json">${embedJson(treaties)}</script>`
        : '') +
      (Object.keys(preceptos).length > 0
        ? `<script id="${PRECEPTO_PRELOAD_ELEMENT_ID}" type="application/json">${embedJson(preceptos)}</script>`
        : '') +
      (haySentencias
        ? `<script id="${SENTENCIA_PRELOAD_ELEMENT_ID}" type="application/json">${embedJson(sentencias)}</script>`
        : '')
  );
  html = replaceOnce(html, 'title', PATTERNS.title, `<title>${title}</title>`);
  html = replaceOnce(
    html,
    'meta description',
    PATTERNS.description,
    `<meta name="description" content="${description}" />`
  );
  html = replaceOnce(
    html,
    'robots',
    PATTERNS.robots,
    `<meta name="robots" content="${route.robots}" />`
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
