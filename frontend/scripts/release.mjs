/**
 * Fuente única del identificador de despliegue.
 *
 * Lo consumen dos piezas que tienen que coincidir siempre: el `define` del
 * bundle (`vite.config.ts`) y el manifiesto `/version.json` que publica
 * `build-version.mjs`. Si divergieran, el navegador se recargaría en bucle o
 * no se recargaría nunca, y ninguna de las dos cosas avisa.
 */
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDir, '../..');

function gitRevision() {
  try {
    return execFileSync('git', ['rev-parse', '--short=12', 'HEAD'], {
      cwd: repositoryRoot,
    })
      .toString()
      .trim();
  } catch {
    return 'local';
  }
}

/**
 * @param {string} [mode] modo de Vite, para resolver el `.env` correspondiente.
 * @returns {string} revisión corta del despliegue, o `local` fuera de un repo.
 */
export function resolveRelease(mode = 'production') {
  const env = loadEnv(mode, repositoryRoot, '');
  return env.VITE_SENTRY_RELEASE || process.env.COMMIT_REF?.slice(0, 12) || gitRevision();
}
