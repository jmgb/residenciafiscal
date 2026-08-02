#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..');
const publicDir = join(frontendDir, 'public');
const routes = JSON.parse(readFileSync(join(frontendDir, 'src/data/countryRoutes.json'), 'utf8'));
const staticRoutes = JSON.parse(
  readFileSync(join(frontendDir, 'src/data/staticRoutes.json'), 'utf8')
);

const normativa = JSON.parse(readFileSync(join(publicDir, 'data/normativa.json'), 'utf8'));

const SITE_URL = 'https://residenciafiscal.org';
// Solo entra lo indexable. Cada país declara su propia frecuencia y prioridad:
// `/espana` tiene corpus y cambia; una jurisdicción sin corpus publica el
// convenio de doble imposición con España, que se mueve muy de tarde en tarde.
// Las fichas de precepto publican texto legal consolidado, que cambia aún
// menos: `yearly` y prioridad baja, el valor está en el long-tail.
const publicRoutes = [
  ...routes
    .filter((route) => route.indexable)
    .map((route) => ({ path: route.path, ...route.sitemap })),
  ...staticRoutes
    .filter((route) => route.indexable)
    .map((route) => ({ path: route.path, ...route.sitemap })),
  ...normativa.map((entry) => ({
    path: `/espana/normativa/${entry.slug}`,
    changefreq: 'yearly',
    priority: '0.4',
  })),
];

// Sin `lastmod` a propósito. La fecha que Google espera ahí es la de la última
// modificación significativa de la página, y este build no dispone de ninguna
// fiable: `vigenteDesde` es la vigencia jurídica (año 1967 en una página
// publicada ayer) y la fecha del build sería ruido en cada deploy. Antes que
// mentir, se omite; `tests/test_frontend_seo_assets.py` lo fija.

const escapeXml = (value) =>
  value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const entries = publicRoutes
  .map((route) => {
    const lastmod = route.lastmod ? `\n    <lastmod>${escapeXml(route.lastmod)}</lastmod>` : '';
    return `  <url>\n    <loc>${escapeXml(`${SITE_URL}${route.path}`)}</loc>${lastmod}\n    <changefreq>${route.changefreq}</changefreq>\n    <priority>${route.priority}</priority>\n  </url>`;
  })
  .join('\n');

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${entries}\n</urlset>\n`;
writeFileSync(join(publicDir, 'sitemap.xml'), sitemap, 'utf8');
console.log(
  `[build-sitemap] ${publicRoutes.length} rutas indexables escritas en public/sitemap.xml`
);
