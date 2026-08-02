#!/usr/bin/env node
/**
 * Materializa en el frontend la proyección pública de las sentencias.
 *
 * La fuente es `knowledge/jurisprudencia-v3/publico/`, que genera
 * `src/export_public_judgments.py` con allowlist, estado calculado y hashes.
 * Este script **no decide** qué se publica: solo materializa lo que el
 * manifiesto ya declara publicable, verifica que cada fichero coincide con su
 * hash y hace visible el estado editorial `published` cuando corresponda.
 *
 *   public/data/sentencias.json                 índices ligeros por jurisdicción
 *   public/data/sentencias/<pais>/<slug>.json  fichas completas, aisladas por país
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
const DEFAULT_SOURCES = [{ jurisdiction: 'es', sourceDir: SOURCE_DIR }];

/** Estados del manifiesto que un build público puede materializar. */
const PUBLIC_STATES = ['published'];
/** Lo que añade un Deploy Preview privado. Nunca es indexable. */
const PREVIEW_STATES = ['internal_preview', 'publishable'];

export function buildSentencias({
  sourceDir,
  sources,
  targetDir = TARGET_DIR,
  includePreview = false,
} = {}) {
  const configuredSources = sources ?? [{ jurisdiction: 'es', sourceDir: sourceDir ?? SOURCE_DIR }];
  const indexFile = join(targetDir, 'sentencias.json');
  const fichaDir = join(targetDir, 'sentencias');

  mkdirSync(targetDir, { recursive: true });
  rmSync(fichaDir, { recursive: true, force: true });
  const allowed = new Set(includePreview ? [...PUBLIC_STATES, ...PREVIEW_STATES] : PUBLIC_STATES);
  const jurisdictionIndexes = {};
  let total = 0;
  let preview = 0;

  for (const configuredSource of configuredSources) {
    const manifestFile = join(configuredSource.sourceDir, 'manifest.json');
    if (!existsSync(manifestFile)) {
      // Sin fuente no se publica nada: es el estado seguro, no un fallback que
      // conserve fichas viejas cuyo estado de revisión ya no se puede comprobar.
      process.stderr.write(
        `[sentencias] No existe ${manifestFile}; se escribe un índice vacío para ${configuredSource.jurisdiction}.\n` +
          '[sentencias] Regenera su proyección pública antes de desplegar contenido.\n'
      );
      jurisdictionIndexes[configuredSource.jurisdiction] = emptyJurisdictionIndex(
        configuredSource.jurisdiction
      );
      continue;
    }

    const manifest = JSON.parse(readFileSync(manifestFile, 'utf8'));
    if (manifest.jurisdiction !== configuredSource.jurisdiction) {
      throw new Error(
        `${manifestFile}: declara la jurisdicción «${manifest.jurisdiction}», ` +
          `pero la fuente está configurada como «${configuredSource.jurisdiction}».`
      );
    }
    if (jurisdictionIndexes[manifest.jurisdiction]) {
      throw new Error(`La jurisdicción «${manifest.jurisdiction}» aparece más de una vez.`);
    }

    const selected = manifest.judgments.filter((entry) => allowed.has(entry.publicationState));
    const jurisdictionFichaDir = join(fichaDir, manifest.jurisdiction);
    if (selected.length > 0) mkdirSync(jurisdictionFichaDir, { recursive: true });

    for (const entry of selected) {
      const source = join(configuredSource.sourceDir, `${entry.judgmentId}.public.json`);
      const raw = readFileSync(source, 'utf8');
      const digest = createHash('sha256').update(raw, 'utf8').digest('hex');
      if (digest !== entry.projectionSha256) {
        throw new Error(
          `${entry.judgmentId}: el hash de la proyección no coincide con el manifiesto. ` +
            'Regenera la exportación pública; no se publica un fichero sin verificar.'
        );
      }
      const projection = JSON.parse(raw);
      const expectedProjectionState =
        entry.publicationState === 'published' ? 'publishable' : entry.publicationState;
      if (
        projection.judgment?.judgmentId !== entry.judgmentId ||
        projection.publicationState !== expectedProjectionState ||
        projection.jurisdiction !== manifest.jurisdiction
      ) {
        throw new Error(
          `${entry.judgmentId}: la identidad, jurisdicción o estado de la proyección no coincide con el manifiesto.`
        );
      }
      const materialized =
        entry.publicationState === 'published'
          ? { ...projection, publicationState: 'published' }
          : projection;
      // Las previews conservan exactamente los bytes de la proyección
      // verificada. Solo `published` materializa el ascenso editorial.
      const output =
        entry.publicationState === 'published' ? `${JSON.stringify(materialized, null, 2)}\n` : raw;
      writeFileSync(join(jurisdictionFichaDir, `${entry.judgmentId}.json`), output, 'utf8');
    }

    jurisdictionIndexes[manifest.jurisdiction] = {
      ...emptyJurisdictionIndex(manifest.jurisdiction),
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
    total += selected.length;
    preview += selected.filter((entry) => entry.publicationState !== 'published').length;
  }

  const index = {
    schemaVersion: 'residenciafiscal-sentencias-index/2',
    jurisdictions: jurisdictionIndexes,
  };
  writeFileSync(indexFile, `${JSON.stringify(index, null, 2)}\n`, 'utf8');

  return { total, preview, jurisdictions: Object.keys(jurisdictionIndexes).length };
}

function emptyJurisdictionIndex(jurisdiction) {
  return {
    jurisdiction,
    candidates: 0,
    includesPreview: false,
    judgments: [],
  };
}

function main() {
  const includePreview = process.env.SENTENCIAS_PREVIEW === '1';
  const { total, preview, jurisdictions } = buildSentencias({
    sources: DEFAULT_SOURCES,
    includePreview,
  });
  process.stdout.write(
    `[sentencias] ${total} fichas de ${jurisdictions} jurisdicciones ` +
      `(${preview} en preview, noindex) -> public/data/\n`
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
