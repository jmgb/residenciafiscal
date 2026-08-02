import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
// @ts-expect-error - script de build en JavaScript, sin tipos
import { buildSentencias } from '../scripts/build-sentencias.mjs';

/**
 * El build no decide qué se publica: materializa lo que el manifiesto declara.
 *
 * Lo que se comprueba aquí es el fail-closed. Un caso en `internal_preview` no
 * puede llegar a producción por olvidar una variable de entorno, y una
 * proyección cuyo hash no cuadra con el manifiesto no se publica en absoluto:
 * el fichero podría haberse editado a mano después de la revisión.
 */
const ENTRY = {
  judgmentId: 'san-1210-2023',
  roj: 'SAN 1210/2023',
  court: 'Audiencia Nacional',
  decisionDate: '2023-03-22',
  taxYears: [2014],
  criterionIds: ['CRIT_183_DIAS'],
  outcomes: ['GANA_AEAT'],
  jurisdictions: ['es'],
  legalReview: 'AGENT_REVIEWED',
};

let sourceDir: string;
let secondSourceDir: string;
let targetDir: string;

function writeSource(
  judgments: Array<Record<string, unknown>>,
  { directory = sourceDir, jurisdiction = 'es' } = {}
) {
  const entries: Array<Record<string, unknown>> = judgments.map((judgment) => {
    const publicationState =
      judgment.publicationState === 'published' ? 'publishable' : judgment.publicationState;
    const contenido = `${JSON.stringify({
      schemaVersion: 'residenciafiscal-public-judgment/1',
      jurisdiction,
      publicationState,
      judgment: { judgmentId: judgment.judgmentId },
    })}\n`;
    writeFileSync(join(directory, `${judgment.judgmentId}.public.json`), contenido, 'utf8');
    return {
      ...judgment,
      projectionSha256: createHash('sha256').update(contenido, 'utf8').digest('hex'),
      sourceSha256: 'a'.repeat(64),
    };
  });
  writeFileSync(
    join(directory, 'manifest.json'),
    JSON.stringify({
      schemaVersion: 'residenciafiscal-public-judgments/1',
      jurisdiction,
      candidates: entries.length,
      published: entries.filter((entry) => entry.publicationState === 'published').length,
      judgments: entries,
    }),
    'utf8'
  );
}

function readIndex() {
  return JSON.parse(readFileSync(join(targetDir, 'sentencias.json'), 'utf8'));
}

function readJurisdiction(code = 'es') {
  return readIndex().jurisdictions[code];
}

beforeEach(() => {
  sourceDir = mkdtempSync(join(tmpdir(), 'sentencias-src-'));
  secondSourceDir = mkdtempSync(join(tmpdir(), 'sentencias-src-'));
  targetDir = mkdtempSync(join(tmpdir(), 'sentencias-out-'));
  mkdirSync(sourceDir, { recursive: true });
});

afterEach(() => {
  rmSync(sourceDir, { recursive: true, force: true });
  rmSync(secondSourceDir, { recursive: true, force: true });
  rmSync(targetDir, { recursive: true, force: true });
});

describe('build-sentencias', () => {
  it('materializa simultáneamente dos jurisdicciones sin colisiones de slug', () => {
    writeSource([{ ...ENTRY, publicationState: 'published' }]);
    writeSource(
      [
        {
          ...ENTRY,
          judgmentId: 'san-1210-2023',
          roj: 'CE 1210/2023',
          court: "Conseil d'État",
          jurisdictions: ['fr'],
          publicationState: 'published',
        },
      ],
      { directory: secondSourceDir, jurisdiction: 'fr' }
    );

    const resultado = buildSentencias({
      sources: [
        { jurisdiction: 'es', sourceDir },
        { jurisdiction: 'fr', sourceDir: secondSourceDir },
      ],
      targetDir,
    });

    expect(resultado).toEqual({ total: 2, preview: 0, jurisdictions: 2 });
    expect(readIndex()).toMatchObject({
      schemaVersion: 'residenciafiscal-sentencias-index/2',
      jurisdictions: {
        es: { jurisdiction: 'es', judgments: [{ judgmentId: 'san-1210-2023' }] },
        fr: { jurisdiction: 'fr', judgments: [{ judgmentId: 'san-1210-2023' }] },
      },
    });
    expect(existsSync(join(targetDir, 'sentencias', 'es', 'san-1210-2023.json'))).toBe(true);
    expect(existsSync(join(targetDir, 'sentencias', 'fr', 'san-1210-2023.json'))).toBe(true);
  });

  it('sin SENTENCIAS_PREVIEW solo materializa los casos published', () => {
    writeSource([
      { ...ENTRY, publicationState: 'internal_preview' },
      { ...ENTRY, judgmentId: 'sts-1-2020', publicationState: 'published' },
    ]);

    const resultado = buildSentencias({ sourceDir, targetDir });

    expect(resultado.total).toBe(1);
    expect(readJurisdiction().judgments.map((j: { judgmentId: string }) => j.judgmentId)).toEqual([
      'sts-1-2020',
    ]);
    expect(existsSync(join(targetDir, 'sentencias', 'es', 'sts-1-2020.json'))).toBe(true);
    expect(existsSync(join(targetDir, 'sentencias', 'es', 'san-1210-2023.json'))).toBe(false);
  });

  it('materializa en la ficha el estado published concedido por el manifiesto', () => {
    writeSource([{ ...ENTRY, publicationState: 'published' }]);

    buildSentencias({ sourceDir, targetDir });

    const ficha = JSON.parse(
      readFileSync(join(targetDir, 'sentencias', 'es', 'san-1210-2023.json'), 'utf8')
    );
    expect(ficha.publicationState).toBe('published');
  });

  it('con el corpus real de hoy un build público no publica ninguna ficha', () => {
    writeSource([{ ...ENTRY, publicationState: 'internal_preview' }]);

    const resultado = buildSentencias({ sourceDir, targetDir });

    expect(resultado.total).toBe(0);
    expect(readJurisdiction().judgments).toEqual([]);
    // El índice declara cuántos candidatos hay: un listado vacío por falta de
    // aprobación no se puede confundir con un build roto.
    expect(readJurisdiction().candidates).toBe(1);
    expect(readJurisdiction().includesPreview).toBe(false);
  });

  it('en preview añade los internal_preview y lo declara en el índice', () => {
    writeSource([{ ...ENTRY, publicationState: 'internal_preview' }]);

    const resultado = buildSentencias({ sourceDir, targetDir, includePreview: true });

    expect(resultado.total).toBe(1);
    expect(resultado.preview).toBe(1);
    const index = readJurisdiction();
    expect(index.includesPreview).toBe(true);
    expect(index.judgments[0].publicationState).toBe('internal_preview');
    expect(index.judgments[0].legalReview).toBe('AGENT_REVIEWED');
  });

  it('no publica una proyección cuyo hash no coincide con el manifiesto', () => {
    writeSource([{ ...ENTRY, publicationState: 'published' }]);
    writeFileSync(
      join(sourceDir, 'san-1210-2023.public.json'),
      '{"judgment":{"editado":"a mano"}}\n',
      'utf8'
    );

    expect(() => buildSentencias({ sourceDir, targetDir })).toThrow(
      /no coincide con el manifiesto/
    );
  });

  it('sin fuente escribe un índice vacío en vez de conservar fichas viejas', () => {
    const resultado = buildSentencias({ sourceDir, targetDir });

    expect(resultado.total).toBe(0);
    expect(readJurisdiction().judgments).toEqual([]);
    expect(existsSync(join(targetDir, 'sentencias'))).toBe(false);
  });

  it('una ficha retirada del manifiesto desaparece del build', () => {
    writeSource([{ ...ENTRY, publicationState: 'published' }]);
    buildSentencias({ sourceDir, targetDir });
    expect(existsSync(join(targetDir, 'sentencias', 'es', 'san-1210-2023.json'))).toBe(true);

    writeSource([{ ...ENTRY, publicationState: 'internal_preview' }]);
    buildSentencias({ sourceDir, targetDir });

    expect(existsSync(join(targetDir, 'sentencias', 'es', 'san-1210-2023.json'))).toBe(false);
  });
});
