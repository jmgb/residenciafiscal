#!/usr/bin/env node
/**
 * Copia al frontend la proyección pública de las sentencias.
 *
 * La fuente es `knowledge/jurisprudencia-v3/publico/`, que genera
 * `src/export_public_judgments.py` con allowlist, estado calculado y hashes.
 * Este script **no decide** qué se publica: solo materializa lo que el
 * manifiesto ya declara publicable, y verifica que cada fichero coincide con su
 * hash antes de copiarlo.
 *
 *   public/data/sentencias.json          índice ligero para el listado
 *   public/data/sentencias/<slug>.json   la ficha completa de una sentencia
 *
 * **Fail-closed.** Por defecto solo entran los casos `published`. Con el corpus
 * de hoy son cero —los 67 candidatos siguen en `internal_preview` porque su
 * análisis es `AGENT_REVIEWED`—, así que un build público escribe un índice
 * vacío y ninguna ficha, y sin fichero no hay ruta que servir.
 *
 * `SENTENCIAS_PREVIEW=1` añade los `internal_preview`. Es lo que usa el Deploy
 * Preview privado; esas rutas se emiten siempre con `noindex` y nunca entran en
 * el sitemap. La variable no puede ascender nada: el estado viaja en el
 * manifiesto y el prerender lo vuelve a leer de ahí.
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..');
const repoDir = join(frontendDir, '..');

const SOURCE_DIR = join(repoDir, 'knowledge', 'jurisprudencia-v3', 'publico');
const TARGET_DIR = join(frontendDir, 'public', 'data');

/** Estados del manifiesto que un build público puede materializar. */
const PUBLIC_STATES = ['published'];
/** Lo que añade un Deploy Preview privado. Nunca es indexable. */
const PREVIEW_STATES = ['internal_preview', 'publishable'];

export function buildSentencias({
  sourceDir = SOURCE_DIR,
  targetDir = TARGET_DIR,
  includePreview = false,
} = {}) {
  const indexFile = join(targetDir, 'sentencias.json');
  const fichaDir = join(targetDir, 'sentencias');
  const manifestFile = join(sourceDir, 'manifest.json');

  mkdirSync(targetDir, { recursive: true });
  rmSync(fichaDir, { recursive: true, force: true });

  if (!existsSync(manifestFile)) {
    // Sin fuente no se publica nada: es el estado seguro, no un fallback que
    // conserve fichas viejas cuyo estado de revisión ya no se puede comprobar.
    process.stderr.write(
      `[sentencias] No existe ${manifestFile}; se escribe un índice vacío.\n` +
        '[sentencias] Regenéralo con `make export-public-judgments` desde la raíz.\n'
    );
    writeFileSync(indexFile, `${JSON.stringify(emptyIndex(), null, 2)}\n`, 'utf8');
    return { total: 0, preview: 0 };
  }

  const manifest = JSON.parse(readFileSync(manifestFile, 'utf8'));
  const allowed = new Set(includePreview ? [...PUBLIC_STATES, ...PREVIEW_STATES] : PUBLIC_STATES);
  const selected = manifest.judgments.filter((entry) => allowed.has(entry.publicationState));

  mkdirSync(fichaDir, { recursive: true });
  for (const entry of selected) {
    const source = join(sourceDir, `${entry.judgmentId}.public.json`);
    const raw = readFileSync(source, 'utf8');
    const digest = createHash('sha256').update(raw, 'utf8').digest('hex');
    if (digest !== entry.projectionSha256) {
      throw new Error(
        `${entry.judgmentId}: el hash de la proyección no coincide con el manifiesto. ` +
          'Regenera con `make export-public-judgments`; no se publica un fichero sin verificar.'
      );
    }
    writeFileSync(join(fichaDir, `${entry.judgmentId}.json`), raw, 'utf8');
  }

  const index = {
    ...emptyIndex(),
    jurisdiction: manifest.jurisdiction,
    // El índice declara qué contiene: sin esto, una página no podría distinguir
    // un listado vacío porque nada está aprobado de un build roto.
    candidates: manifest.candidates,
    includesPreview: includePreview,
    judgments: selected.map((entry) => ({
      judgmentId: entry.judgmentId,
      roj: entry.roj,
      court: entry.court,
      decisionDate: entry.decisionDate,
      taxYears: entry.taxYears,
      criterionIds: entry.criterionIds,
      outcomes: entry.outcomes,
      jurisdictions: entry.jurisdictions,
      publicationState: entry.publicationState,
      legalReview: entry.legalReview,
    })),
  };
  writeFileSync(indexFile, `${JSON.stringify(index, null, 2)}\n`, 'utf8');

  return {
    total: selected.length,
    preview: selected.filter((entry) => entry.publicationState !== 'published').length,
  };
}

function emptyIndex() {
  return {
    schemaVersion: 'residenciafiscal-sentencias-index/1',
    jurisdiction: 'es',
    candidates: 0,
    includesPreview: false,
    judgments: [],
  };
}

function main() {
  const includePreview = process.env.SENTENCIAS_PREVIEW === '1';
  const { total, preview } = buildSentencias({ includePreview });
  process.stdout.write(
    `[sentencias] ${total} fichas (${preview} en preview, noindex) -> public/data/\n`
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
