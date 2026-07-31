/**
 * El bundle y `/version.json` tienen que hablar del mismo deploy.
 *
 * La comprobación de versión en runtime compara la constante compilada en el
 * bundle con el manifiesto publicado. Si las dos se calculan por su cuenta y
 * divergen, el navegador se recarga en bucle o no se recarga nunca; ninguna de
 * las dos cosas avisa. Este test ata las dos fuentes al mismo cálculo.
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { APP_RELEASE } from '@/lib/app-version';

const FRONTEND_ROOT = join(__dirname, '..');
const outputDir = mkdtempSync(join(tmpdir(), 'rf-version-'));

afterAll(() => {
  rmSync(outputDir, { recursive: true, force: true });
});

function buildVersionManifest(): { release: string } {
  execFileSync('node', [join(FRONTEND_ROOT, 'scripts/build-version.mjs'), outputDir], {
    cwd: FRONTEND_ROOT,
  });
  return JSON.parse(readFileSync(join(outputDir, 'version.json'), 'utf-8'));
}

describe('release del despliegue', () => {
  it('publica un manifiesto con el release del despliegue', () => {
    const manifest = buildVersionManifest();

    expect(typeof manifest.release).toBe('string');
    expect(manifest.release.trim()).not.toBe('');
  });

  it('declara en el bundle el mismo release que publica el manifiesto', () => {
    // `APP_RELEASE` es el valor que `vite.config.ts` compila dentro del bundle;
    // el manifiesto lo calcula por su cuenta desde el mismo módulo compartido.
    expect(APP_RELEASE).toBe(buildVersionManifest().release);
  });
});
