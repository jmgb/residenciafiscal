import { describe, expect, it } from 'vitest';
import {
  productionCorpus,
  productionCorpusReadiness,
  productionVerbatimArtifacts,
} from '../netlify/functions/chat/production-corpus';

describe('corpus productivo del chat', () => {
  it('conecta las 106 sentencias y sus verbatim sin perder las exclusiones de recuperación', () => {
    expect(productionCorpusReadiness).toEqual({
      sampleId: 'jurisprudencia-v3-fase-e',
      sourceCount: 106,
      retrievalDocumentCount: 67,
      retrievalUnitCount: 74,
      verbatimArtifactCount: 106,
      allSourcesHaveVerbatim: true,
    });
    expect(new Set(productionCorpus.sources.map((source) => source.judgment_id))).toEqual(
      new Set(Object.keys(productionVerbatimArtifacts))
    );
  });
});
