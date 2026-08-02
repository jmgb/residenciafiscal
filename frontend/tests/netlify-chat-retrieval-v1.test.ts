import { describe, expect, it } from 'vitest';
import corpus from '../../knowledge/jurisprudencia-v3/retrieval/corpus.json';
import rolloutCorpus from '../../knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json';
import { rankUnits } from '../netlify/functions/chat/retrieval-lexical';
import { retrieveForChat } from '../netlify/functions/chat/structured-retrieval';

describe('recuperación estructurada Netlify V1', () => {
  it.each([
    [
      '¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?',
      'responder',
      [
        'san-1210-2023-residencia-fiscal',
        'san-1226-2021-residencia-fiscal-2011',
        'san-1136-2016-residencia-habitual',
        'san-1071-2025-residencia-fiscal',
        'san-1386-2017-exencion-indemnizacion',
      ],
    ],
    [
      '¿Cómo calcularon los días las sentencias de la muestra?',
      'parcial',
      [
        'san-1386-2017-residencia-fiscal-suiza',
        'san-1210-2023-residencia-fiscal',
        'san-1226-2021-residencia-fiscal-2011',
        'san-1136-2016-residencia-habitual',
        'san-1071-2025-residencia-fiscal',
      ],
    ],
  ])('mantiene paridad con Python para %s', (question, behavior, unitIds) => {
    const result = retrieveForChat(corpus, question, 5);

    expect(result.behavior).toBe(behavior);
    expect(result.hits.map((hit) => hit.unitId)).toEqual(unitIds);
  });

  it('se abstiene ante una faceta que la muestra aún no cubre', () => {
    const result = retrieveForChat(
      corpus,
      '¿Qué son las ausencias esporádicas y cuándo computan?',
      5
    );

    expect(result).toMatchObject({
      behavior: 'abstenerse',
      uncoveredFacets: ['CRIT_AUSENCIAS_ESPORADICAS'],
      hits: [],
    });
  });

  it('prioriza un identificador judicial explícito dentro de las 106', () => {
    expect(
      rankUnits(rolloutCorpus, '¿Qué resolvió SAN 2132/2025 sobre residencia fiscal?')[0]?.unit
        .judgment_id
    ).toBe('san-2132-2025');
    expect(
      rankUnits(rolloutCorpus, 'Resume la STS 3882/2024 y sus pruebas.')[0]?.unit.judgment_id
    ).toBe('sts-3882-2024');
  });

  it('usa la cobertura nueva para responder sobre ausencias esporádicas', () => {
    const result = retrieveForChat(
      rolloutCorpus,
      '¿Qué son las ausencias esporádicas y cuándo computan?',
      5
    );

    expect(result.behavior).toBe('responder');
    expect(result.uncoveredFacets).toEqual([]);
    expect(result.hits[0]).toMatchObject({
      judgmentId: 'sts-107-2018',
      unitId: 'sts-107-2018-residencia-fiscal',
    });
  });

  it('limita la recuperación a autoridad directa cuando se pregunta por el Tribunal Supremo', () => {
    const result = retrieveForChat(
      rolloutCorpus,
      '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
      5
    );

    expect(result.hits.length).toBeGreaterThan(0);
    expect(result.hits.every((hit) => hit.judgmentId.startsWith('sts-'))).toBe(true);
  });
});
