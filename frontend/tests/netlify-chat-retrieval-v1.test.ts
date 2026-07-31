import { describe, expect, it } from 'vitest';
import corpus from '../../knowledge/jurisprudencia-v3/retrieval/corpus.json';
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
        'san-1386-2017-residencia-fiscal-suiza',
      ],
    ],
    [
      '¿Cómo calcularon los días las sentencias de la muestra?',
      'parcial',
      [
        'san-1386-2017-residencia-fiscal-suiza',
        'san-1136-2016-residencia-habitual',
        'san-1226-2021-residencia-fiscal-2011',
        'san-1210-2023-residencia-fiscal',
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
});
