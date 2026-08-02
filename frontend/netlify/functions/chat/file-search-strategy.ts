import {
  type FileCitation,
  type VerbatimArtifact,
  verifyFileCitation,
} from './citation-verification';
import type { StrategyAnswer, StrategySource } from './contracts';
import {
  authorityLabel,
  authorityMatch,
  authorityMetadataFilter,
  requestedJudicialAuthority,
} from './judicial-authority';
import { marginalCost } from './pricing';
import { extractJudgmentIdentifiers } from './retrieval-lexical';
import type { NetlifyChatStrategy, StrategyContext } from './runtime';

const DEFAULT_MODEL = 'gemini-3.5-flash-lite';

export interface Interaction {
  output_text?: string;
  steps?: Array<{
    type?: string;
    content?: Array<{ text?: string; annotations?: FileCitation[] }>;
  }>;
  usage?: {
    total_input_tokens?: number;
    total_output_tokens?: number;
    total_thought_tokens?: number;
    input_tokens_by_modality?: Array<{ modality?: string; tokens?: number }>;
  };
}

export interface GeminiInteractionInput {
  model: string;
  storeName: string;
  prompt: string;
  requestId: string;
  metadataFilter?: string;
}

export interface GeminiFileSearchOptions {
  storeName: string;
  artifacts: Record<string, VerbatimArtifact>;
  interact(input: GeminiInteractionInput, signal: AbortSignal): Promise<Interaction>;
  model?: string;
}

const citations = (interaction: Interaction) =>
  (interaction.steps ?? [])
    .filter((step) => step.type === 'model_output')
    .flatMap((step) => step.content ?? [])
    .flatMap((content) => content.annotations ?? [])
    .filter((annotation) => annotation.type === 'file_citation');

const parseDraft = (serialized: string) => {
  const parsed = JSON.parse(serialized) as Record<string, unknown>;
  const statuses = ['completa', 'parcial', 'pregunta', 'abstención'];
  if (
    !statuses.includes(String(parsed.status)) ||
    typeof parsed.answer !== 'string' ||
    !Array.isArray(parsed.limits) ||
    !parsed.limits.every((item) => typeof item === 'string')
  ) {
    throw new Error('Salida Gemini inválida');
  }
  return parsed as {
    status: 'completa' | 'parcial' | 'pregunta' | 'abstención';
    answer: string;
    limits: string[];
  };
};

const usage = (interaction: Interaction) => {
  const raw = interaction.usage;
  const retrievedDocumentTokens = (raw?.input_tokens_by_modality ?? []).reduce(
    (total, item) =>
      String(item.modality).toLocaleLowerCase().endsWith('document')
        ? total + (item.tokens ?? 0)
        : total,
    0
  );
  const hasCitations = citations(interaction).length > 0;
  return {
    inputTokens: Math.max(0, (raw?.total_input_tokens ?? 0) - retrievedDocumentTokens),
    outputTokens: (raw?.total_output_tokens ?? 0) + (raw?.total_thought_tokens ?? 0),
    retrievedDocumentTokens,
    complete:
      raw?.total_input_tokens !== undefined &&
      raw.total_output_tokens !== undefined &&
      raw.input_tokens_by_modality !== undefined &&
      (!hasCitations || retrievedDocumentTokens > 0),
  };
};

export class GeminiFileSearchStrategy implements NetlifyChatStrategy {
  readonly id = 'gemini_file_search' as const;
  private readonly model: string;

  constructor(private readonly options: GeminiFileSearchOptions) {
    this.model = options.model ?? DEFAULT_MODEL;
  }

  async answer(question: string, context: StrategyContext): Promise<StrategyAnswer> {
    const started = performance.now();
    const judgmentIds = [...extractJudgmentIdentifiers(question)];
    const authorityIntent = requestedJudicialAuthority(question);
    const metadataFilter =
      judgmentIds.length === 1
        ? `judgment_id="${judgmentIds[0]}"`
        : (authorityMetadataFilter(authorityIntent) ?? undefined);
    const authorityInstruction = authorityIntent
      ? ` La pregunta pide ${authorityLabel(authorityIntent)}: usa autoridad directa de ese órgano y no presentes como propia doctrina contenida solo en una sentencia de otro tribunal.`
      : '';
    const interaction = await this.options.interact(
      {
        model: this.model,
        storeName: this.options.storeName,
        requestId: context.requestId,
        metadataFilter,
        prompt:
          'Actúa como asistente de investigación jurisprudencial sobre residencia fiscal. Usa exclusivamente los PDF recuperados mediante File Search. Distingue hechos, valoración y resultado; no predigas el caso del usuario ni uses conocimiento externo. Si falta cobertura, responde parcial, pregunta o abstención.' +
          authorityInstruction +
          '\n\nPregunta del usuario:\n' +
          question,
      },
      context.signal
    );
    const output =
      interaction.output_text ??
      (interaction.steps ?? [])
        .filter((step) => step.type === 'model_output')
        .flatMap((step) => step.content ?? [])
        .map((content) => content.text ?? '')
        .join('');
    const draft = parseDraft(output);
    const citationCandidates = citations(interaction);
    const verified = citationCandidates
      .map((citation) => verifyFileCitation(citation, this.options.artifacts))
      .filter((source): source is StrategySource => source !== null)
      .filter(
        (source, index, all) =>
          all.findIndex(
            (candidate) =>
              candidate.judgment_id === source.judgment_id &&
              candidate.page === source.page &&
              candidate.quote === source.quote
          ) === index
      );
    const cost = marginalCost(this.model, usage(interaction));
    if (['completa', 'parcial'].includes(draft.status) && draft.answer && !verified.length) {
      return {
        strategy: this.id,
        status: 'error',
        text: '',
        sources: [],
        limits: [
          citations(interaction).length
            ? 'Se retiraron citas no verificables contra el PDF original.'
            : 'El proveedor no devolvió citas verificables para la respuesta.',
          ...draft.limits,
        ],
        cost,
        model: this.model,
        reasoning_effort: null,
        latency_ms: Math.round(performance.now() - started),
        diagnostics: {
          authority_intent: authorityIntent,
          authority_match: authorityMatch(authorityIntent, []),
          retrieval_filter: metadataFilter ?? null,
          retrieved_judgment_ids: [],
          citation_candidates: citationCandidates.length,
          citation_verified: 0,
          failure_code: 'citation_verification',
          error_name: null,
        },
      };
    }
    const directAuthority = authorityMatch(
      authorityIntent,
      verified.map((source) => source.judgment_id)
    );
    const authorityLimit =
      authorityIntent && directAuthority === 'missing'
        ? `Las citas verificadas no proceden directamente del ${authorityLabel(authorityIntent)}.`
        : null;
    const finalStatus = authorityLimit && draft.status === 'completa' ? 'parcial' : draft.status;
    return {
      strategy: this.id,
      status: finalStatus,
      text: draft.answer,
      sources: verified,
      limits: [...draft.limits, ...(authorityLimit ? [authorityLimit] : [])],
      cost,
      model: this.model,
      reasoning_effort: null,
      latency_ms: Math.round(performance.now() - started),
      diagnostics: {
        authority_intent: authorityIntent,
        authority_match: directAuthority,
        retrieval_filter: metadataFilter ?? null,
        retrieved_judgment_ids: [...new Set(verified.map((source) => source.judgment_id))],
        citation_candidates: citationCandidates.length,
        citation_verified: verified.length,
        failure_code: null,
        error_name: null,
      },
    };
  }
}
