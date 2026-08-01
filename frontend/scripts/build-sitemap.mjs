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

const SITE_URL = 'https://residenciafiscal.org';
// Solo entra lo indexable. Cada país declara su propia frecuencia y prioridad:
// `/espana` tiene corpus y cambia; una jurisdicción sin corpus publica el
// convenio de doble imposición con España, que se mueve muy de tarde en tarde.
const publicRoutes = [
  ...routes
    .filter((route) => route.indexable)
    .map((route) => ({ path: route.path, ...route.sitemap })),
  ...staticRoutes
    .filter((route) => route.indexable)
    .map((route) => ({ path: route.path, ...route.sitemap })),
];

const escapeXml = (value) =>
  value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const entries = publicRoutes
  .map(
    (route) =>
      `  <url>\n    <loc>${escapeXml(`${SITE_URL}${route.path}`)}</loc>\n    <changefreq>${route.changefreq}</changefreq>\n    <priority>${route.priority}</priority>\n  </url>`
  )
  .join('\n');

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${entries}\n</urlset>\n`;
writeFileSync(join(publicDir, 'sitemap.xml'), sitemap, 'utf8');
console.log(
  `[build-sitemap] ${publicRoutes.length} rutas indexables escritas en public/sitemap.xml`
);
