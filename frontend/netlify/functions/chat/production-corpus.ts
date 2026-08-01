import corpus from '../../../../knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json';
import { productionVerbatimArtifacts } from './verbatim-artifacts.generated';

const sourceIds = new Set(corpus.sources.map((source) => source.judgment_id));
const verbatimIds = new Set(Object.keys(productionVerbatimArtifacts));
const allSourcesHaveVerbatim =
  sourceIds.size === verbatimIds.size &&
  [...sourceIds].every((judgmentId) => verbatimIds.has(judgmentId));

export const productionCorpusReadiness = Object.freeze({
  sampleId: corpus.sample_id,
  sourceCount: sourceIds.size,
  retrievalDocumentCount: new Set(corpus.units.map((unit) => unit.judgment_id)).size,
  retrievalUnitCount: corpus.units.length,
  verbatimArtifactCount: verbatimIds.size,
  allSourcesHaveVerbatim,
});

if (
  productionCorpusReadiness.sourceCount !== 106 ||
  productionCorpusReadiness.retrievalDocumentCount !== 67 ||
  productionCorpusReadiness.retrievalUnitCount !== 74 ||
  !allSourcesHaveVerbatim
) {
  throw new Error('Los artefactos productivos del chat no corresponden al rollout de 106');
}

export const productionCorpus = corpus;
export { productionVerbatimArtifacts };
