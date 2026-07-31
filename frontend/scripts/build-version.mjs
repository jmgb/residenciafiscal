/**
 * Publica `version.json`, el manifiesto que delata que hay un deploy nuevo.
 *
 * La SPA lo consulta al arrancar y cada vez que el navegador vuelve a la
 * pestaña: es lo único que permite a un móvil con la pestaña abierta desde hace
 * días enterarse de que su bundle ya no es el vigente. Se sirve con `no-store`
 * (ver netlify.toml); no lleva fecha de build a propósito, porque cambiaría en
 * cada compilación del mismo commit y provocaría recargas sin motivo.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolveRelease } from './release.mjs';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(scriptDir, '..');
const outputDir = resolve(frontendDir, process.argv[2] ?? 'dist');

mkdirSync(outputDir, { recursive: true });

const manifestFile = join(outputDir, 'version.json');
writeFileSync(manifestFile, `${JSON.stringify({ release: resolveRelease() }, null, 2)}\n`, 'utf8');
console.log(`[version] Generated ${manifestFile}`);
