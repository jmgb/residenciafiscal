import type { MarginalCost } from './contracts';
import pricing from './pricing.generated.json';

type CatalogModel = keyof typeof pricing.models;

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  retrievedDocumentTokens: number;
  complete: boolean;
}

export const marginalCost = (model: string, usage: TokenUsage): MarginalCost => {
  const rates = pricing.models[model as CatalogModel];
  if (!rates) throw new Error(`Modelo sin tarifa en el catálogo compartido: ${model}`);
  const input = usage.inputTokens + usage.retrievedDocumentTokens;
  const microusd = Math.round(
    input * rates.input_usd_per_mtok + usage.outputTokens * rates.output_usd_per_mtok
  );
  return {
    currency: 'USD',
    amount_usd: (microusd / 1_000_000).toFixed(6),
    cost_microusd: microusd,
    measurement: usage.complete ? 'ACTUAL' : 'ESTIMATED',
    scope: 'REQUEST_MARGINAL',
    pricing_version: pricing.catalog_version,
    input_tokens: usage.inputTokens,
    output_tokens: usage.outputTokens,
    retrieved_document_tokens: usage.retrievedDocumentTokens,
    excludes_corpus_preparation: true,
  };
};

export const zeroCost = (model = 'gpt-5.6-luna') =>
  marginalCost(model, {
    inputTokens: 0,
    outputTokens: 0,
    retrievedDocumentTokens: 0,
    complete: true,
  });
