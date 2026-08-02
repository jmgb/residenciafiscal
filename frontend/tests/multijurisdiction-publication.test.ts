import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { render } from '@/entry-server';
// @ts-expect-error - scripts de build en JavaScript, sin tipos
import { buildSentencias } from '../scripts/build-sentencias.mjs';
// @ts-expect-error - módulo compartido por los generadores Node, sin tipos
import { sentenciaRouteInventory } from '../scripts/sentencia-route-inventory.mjs';

const temporales: string[] = [];

function temporal(prefix: string): string {
  const directory = mkdtempSync(join(tmpdir(), prefix));
  temporales.push(directory);
  return directory;
}

function writeCorpus(sourceDir: string, jurisdiction: string, roj: string) {
  const judgmentId = 'residencia-1-2026';
  const projection = `${JSON.stringify({
    schemaVersion: 'residenciafiscal-public-judgment/1',
    jurisdiction,
    publicationState: 'publishable',
    judgment: { judgmentId },
  })}\n`;
  writeFileSync(join(sourceDir, `${judgmentId}.public.json`), projection, 'utf8');
  writeFileSync(
    join(sourceDir, 'manifest.json'),
    JSON.stringify({
      schemaVersion: 'residenciafiscal-public-judgments/1',
      jurisdiction,
      candidates: 1,
      published: 1,
      judgments: [
        {
          judgmentId,
          roj,
          court: jurisdiction === 'es' ? 'Tribunal Supremo' : "Conseil d'État",
          decisionDate: '2026-01-15',
          taxYears: [2024],
          criterionIds: ['CRIT_183_DIAS'],
          outcomes: ['GANA_CONTRIBUYENTE'],
          jurisdictions: [jurisdiction],
          publicationState: 'published',
          legalReview: 'HUMAN_APPROVED',
          projectionSha256: createHash('sha256').update(projection, 'utf8').digest('hex'),
          sourceSha256: 'a'.repeat(64),
        },
      ],
    }),
    'utf8'
  );
}

afterEach(() => {
  for (const directory of temporales.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

describe('publicación multijurisdicción de sentencias', () => {
  it('lleva España y una segunda jurisdicción al inventario SEO y al HTML prerenderizado', () => {
    const sourceEs = temporal('sentencias-es-');
    const sourceFr = temporal('sentencias-fr-');
    const targetDir = temporal('sentencias-public-');
    writeCorpus(sourceEs, 'es', 'STS 1/2026');
    writeCorpus(sourceFr, 'fr', 'CE 1/2026');

    buildSentencias({
      sources: [
        { jurisdiction: 'es', sourceDir: sourceEs },
        { jurisdiction: 'fr', sourceDir: sourceFr },
      ],
      targetDir,
    });

    const manifest = JSON.parse(readFileSync(join(targetDir, 'sentencias.json'), 'utf8'));
    const routes = sentenciaRouteInventory(manifest);
    const publishedRoutes = sentenciaRouteInventory(manifest, { publishedOnly: true });
    const expectedPaths = [
      '/espana/sentencias',
      '/espana/sentencias/residencia-1-2026',
      '/francia/sentencias',
      '/francia/sentencias/residencia-1-2026',
    ];

    // Sitemap filtra a published; redirects y prerender consumen el inventario
    // completo materializado (que en un deploy preview puede contener noindex).
    expect(publishedRoutes.map((route: { path: string }) => route.path)).toEqual(expectedPaths);
    expect(routes.map((route: { path: string }) => route.path)).toEqual(expectedPaths);
    expect(routes.map((route: { path: string }) => `${route.path}/index.html`)).toEqual(
      expectedPaths.map((path) => `${path}/index.html`)
    );

    const frenchIndex = manifest.jurisdictions.fr;
    const html = render(
      '/francia/sentencias',
      {},
      {},
      {
        indexes: { fr: frenchIndex },
        fichas: {},
      }
    );
    expect(html).toMatch(/Sentencias sobre residencia fiscal en (?:<!-- -->)?Francia/);
    expect(html).toContain('href="/francia/sentencias/residencia-1-2026"');
    expect(html).not.toContain('href="/espana/sentencias/residencia-1-2026"');
  });
});
