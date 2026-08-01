import type { StrategyAnswer } from './contracts';
import { buildEvidenceBundle } from './evidence-bundle';
import { marginalCost, zeroCost } from './pricing';
import type { NetlifyChatStrategy, StrategyContext } from './runtime';
import { retrieveForChat } from './structured-retrieval';

const MODEL = 'gpt-5.6-luna';
const REASONING_EFFORT = 'high';

const systemPrompt =
  'Actúa como asistente de investigación jurisprudencial sobre residencia fiscal de personas físicas en IRPF y CDI, no sobre extranjería. Responde solo con el contexto recuperado. Distingue hechos acreditados, valoración judicial y resultado; muestra contraste cuando exista. No predigas el caso del usuario ni uses conocimiento externo. Recibirás fragmentos literales con IDs E<n>: devuelve únicamente los IDs que respaldan la respuesta y no reconstruyas citas en answer. Incluye siempre limits y evidence_ids, aunque sean listas vacías.';

export interface StructuredDraft {
  status: 'completa' | 'parcial' | 'pregunta' | 'abstención';
  answer: string;
  limits: string[];
  evidence_ids: string[];
}

export interface StructuredWriterResult {
  draft: StructuredDraft;
  usage: { input_tokens: number; output_tokens: number; complete: boolean };
  model: string;
}

export interface StructuredWriter {
  write(input: {
    systemPrompt: string;
    userPrompt: string;
    model: string;
    reasoningEffort: 'high';
    requestId: string;
    signal: AbortSignal;
  }): Promise<StructuredWriterResult>;
}

const nonAnswerText = (
  status: StrategyAnswer['status'],
  reasons: string[],
  missingFacts: string[],
  uncoveredFacets: string[]
) => {
  if (status === 'pregunta' && missingFacts.length) {
    return `Para buscar casos realmente comparables necesito que indiques: ${missingFacts.join('; ')}.`;
  }
  if (status === 'abstención') {
    return `El corpus actual no cubre con suficiente precisión esta cuestión: ${uncoveredFacets.join('; ') || reasons.join(' ')}.`;
  }
  return reasons.join(' ');
};

export class CurrentStructuredStrategy implements NetlifyChatStrategy {
  readonly id = 'current_structured' as const;

  constructor(
    private readonly corpus: unknown,
    private readonly writer: StructuredWriter
  ) {}

  async answer(question: string, context: StrategyContext): Promise<StrategyAnswer> {
    const started = performance.now();
    const retrieval = retrieveForChat(this.corpus, question, 5);
    const status = {
      responder: 'completa',
      parcial: 'parcial',
      preguntar: 'pregunta',
      abstenerse: 'abstención',
    }[retrieval.behavior] as StrategyAnswer['status'];
    const retrievalLimits = [...retrieval.missingFacts, ...retrieval.uncoveredFacets];
    if (status === 'pregunta' || status === 'abstención') {
      return {
        strategy: this.id,
        status,
        text: nonAnswerText(
          status,
          retrieval.behaviorReasons,
          retrieval.missingFacts,
          retrieval.uncoveredFacets
        ),
        sources: [],
        limits: retrievalLimits,
        cost: zeroCost(MODEL),
        model: 'deterministic-structured-v3',
        reasoning_effort: null,
        latency_ms: Math.round(performance.now() - started),
      };
    }

    const bundle = buildEvidenceBundle(this.corpus, retrieval, question);
    const written = await this.writer.write({
      systemPrompt,
      userPrompt: `Pregunta del usuario:\n${question}\n\nContexto estructurado recuperado:\n${bundle.contextJson}`,
      model: MODEL,
      reasoningEffort: REASONING_EFFORT,
      requestId: context.requestId,
      signal: context.signal,
    });
    const cost = marginalCost(MODEL, {
      inputTokens: written.usage.input_tokens,
      outputTokens: written.usage.output_tokens,
      retrievedDocumentTokens: 0,
      complete: written.usage.complete,
    });
    const evidenceIds = [...new Set(written.draft.evidence_ids)];
    const unknown = evidenceIds.filter((id) => !bundle.sourcesByEvidenceId.has(id));
    if (
      unknown.length ||
      (['completa', 'parcial'].includes(written.draft.status) && !evidenceIds.length)
    ) {
      const reason = unknown.length
        ? `El redactor devolvió evidencias desconocidas: ${unknown.join(', ')}.`
        : 'El redactor no vinculó ninguna evidencia a la respuesta sustantiva.';
      return {
        strategy: this.id,
        status: 'error',
        text: '',
        sources: [],
        limits: [reason],
        cost,
        model: written.model,
        reasoning_effort: REASONING_EFFORT,
        latency_ms: Math.round(performance.now() - started),
      };
    }
    const finalStatus =
      retrieval.behavior === 'parcial' && written.draft.status === 'completa'
        ? 'parcial'
        : written.draft.status;
    return {
      strategy: this.id,
      status: finalStatus,
      text: written.draft.answer,
      sources: evidenceIds.map(
        (id) =>
          bundle.sourcesByEvidenceId.get(id) as NonNullable<
            ReturnType<typeof bundle.sourcesByEvidenceId.get>
          >
      ),
      limits: [...retrievalLimits, ...written.draft.limits],
      cost,
      model: written.model,
      reasoning_effort: REASONING_EFFORT,
      latency_ms: Math.round(performance.now() - started),
    };
  }
}
