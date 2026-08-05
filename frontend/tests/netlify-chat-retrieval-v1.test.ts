import { describe, expect, it } from 'vitest';
import corpus from '../../knowledge/jurisprudencia-v3/retrieval/corpus.json';
import rolloutCorpus from '../../knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json';
import { buildEvidenceBundle } from '../netlify/functions/chat/evidence-bundle';
import { productionVerbatimArtifacts } from '../netlify/functions/chat/production-corpus';
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

  it('amplía el anclaje literal con contexto verificable de la página original', () => {
    const question = '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?';
    const retrieval = retrieveForChat(rolloutCorpus, question, 5);
    const bundle = buildEvidenceBundle(
      rolloutCorpus,
      retrieval,
      question,
      productionVerbatimArtifacts
    );
    const source = [...bundle.sourcesByEvidenceId.values()].find(
      (candidate) =>
        candidate.judgment_id === 'sts-3585-2024' &&
        candidate.quote.includes('consumos efectuados con las tarjetas virtuales')
    );

    expect(source?.quote).toContain('consumos efectuados con las tarjetas virtuales');
    expect(source?.quote).toContain('no se ha acreditado en forma');
    expect(source?.quote.length).toBeGreaterThan(250);
  });

  it('recupera el indicio de cuotas de gimnasio para la pregunta real de producción', () => {
    const question =
      'si una persona se apunta al gym o si usa su teléfono movil en españa, esto la agencia tributaria lo tiene en cuenta para el computo de los 183 días?';
    const retrieval = retrieveForChat(rolloutCorpus, question, 5);

    expect(retrieval.behavior).toBe('parcial');
    expect(retrieval.hits.map((hit) => hit.judgmentId)).toContain('san-2347-2022');

    const bundle = buildEvidenceBundle(
      rolloutCorpus,
      retrieval,
      question,
      productionVerbatimArtifacts
    );
    const gymSource = [...bundle.sourcesByEvidenceId.values()].find(
      (source) => source.judgment_id === 'san-2347-2022' && /gimnasios/i.test(source.quote)
    );

    expect(gymSource?.quote).toContain('cuotas de clubs deportivos');
    expect(gymSource?.quote).toContain('gimnasios');
  });

  it('empareja la prueba de Hacienda con la valoración judicial en la pregunta de los 183 días', () => {
    const question =
      '¿Qué puede hacer Hacienda para demostrar que he estado en España más de 183 días?';
    const retrieval = retrieveForChat(rolloutCorpus, question, 5);
    const bundle = buildEvidenceBundle(
      rolloutCorpus,
      retrieval,
      question,
      productionVerbatimArtifacts
    );
    const sources = [...bundle.sourcesByEvidenceId.values()].filter(
      (source) => source.judgment_id === 'san-6289-2022'
    );
    const purposes = [...bundle.sourcesByEvidenceId.keys()]
      .filter((id) => bundle.sourcesByEvidenceId.get(id)?.judgment_id === 'san-6289-2022')
      .map((id) => bundle.purposesByEvidenceId.get(id));

    expect(retrieval.hits.map((hit) => hit.judgmentId)).toContain('san-6289-2022');
    expect(sources.length).toBeGreaterThan(2);
    expect(sources.some((source) => source.quote.includes('no existen indicios suﬁcientes'))).toBe(
      true
    );
    expect(
      sources.some((source) =>
        source.quote
          .replace(/\s+/g, ' ')
          .includes('tampoco sirve por si mismo para acreditar la residencia en España')
      )
    ).toBe(true);
    expect(purposes).toEqual(['HOLDING', 'REASONING', 'BURDEN_OF_PROOF', 'EVIDENCE']);
  });

  it('no interpreta el verbo genérico apunta como una alta en el gimnasio', () => {
    const ranked = rankUnits(
      rolloutCorpus,
      '¿Qué apunta el tribunal sobre el cómputo de los 183 días?'
    );

    expect(ranked[0]?.unit.judgment_id).not.toBe('san-2347-2022');
  });
});
