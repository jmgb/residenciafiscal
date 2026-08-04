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
export const FILE_SEARCH_PROMPT_VERSION = 'file-search-authority-v8';

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
    total_tool_use_tokens?: number;
    input_tokens_by_modality?: Array<{ modality?: string; tokens?: number }>;
    tool_use_tokens_by_modality?: Array<{ modality?: string; tokens?: number }>;
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

const retrievalHints = (question: string): string => {
  const normalized = question.toLocaleLowerCase('es').normalize('NFKD').replace(/\p{M}/gu, '');
  const hints: string[] = [];
  if (/\b(?:gym|gimnasio|gimnasios)\b/.test(normalized)) {
    hints.push(
      'En la búsqueda, “gym” equivale a “gimnasio”, “cuotas de clubs deportivos” y “centros deportivos”: busca por separado la frase exacta “cuotas de clubs deportivos, de golf, polo, futbol o gimnasios”. Si ese pasaje aparece citado y otra parte de la pregunta queda sin respaldo, responde de forma parcial sobre el gimnasio y declara la otra carencia en limits.'
    );
  }
  if (/\b(?:telefono|movil)\b/.test(normalized)) {
    hints.push(
      'El mero uso o contrato de teléfono no presupone geolocalización ni presencia en una fecha concreta.'
    );
  }
  return hints.length ? `\n\nPistas terminológicas y de alcance:\n${hints.join('\n')}` : '';
};

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
  const legacyDocumentTokens = (raw?.input_tokens_by_modality ?? []).reduce(
    (total, item) =>
      String(item.modality).toLocaleLowerCase().endsWith('document')
        ? total + (item.tokens ?? 0)
        : total,
    0
  );
  const retrievedDocumentTokens = raw?.total_tool_use_tokens ?? legacyDocumentTokens;
  const hasCitations = citations(interaction).length > 0;
  return {
    inputTokens: Math.max(0, (raw?.total_input_tokens ?? 0) - legacyDocumentTokens),
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
    const prompt =
      'Actúa como asistente de investigación jurisprudencial sobre residencia fiscal. Usa exclusivamente los PDF recuperados mediante File Search. Solo emite una respuesta sustantiva con estado completa o parcial si File Search aporta al menos un pasaje citado por File Search que respalde la respuesta; si no hay ningún pasaje citado, pregunta o abstente. Responde primero y de forma directa a lo preguntado, en una o dos frases, y desarrolla después solo los puntos necesarios. Si la pregunta tiene varias partes, contesta cada parte o usa estado parcial e identifica la parte no resuelta; resuelve cada parte por separado. Si pregunta cuándo, cómo o salvo qué, expresa de forma explícita la condición y sus excepciones respaldadas; no las dejes implícitas. Distingue hechos acreditados, argumentos de las partes, valoración de la instancia, doctrina del tribunal consultado y resultado. No atribuyas al tribunal argumentos de las partes ni razonamientos que la resolución se limite a citar. Separa permanencia física, ausencias esporádicas, certificados fiscales extranjeros y reglas de desempate de CDI si la pregunta mezcla esos conceptos. Ante datos de vida cotidiana, una mera alta, titularidad o pago de una cuota no prueba por sí sola presencia en una fecha: distingue ese dato del uso efectivo atribuible al contribuyente y de su valoración conjunta con otros indicios. No desarrolles dimensiones que la pregunta no necesita. No equipares desvirtuar el número de días de presencia con acreditar residencia fiscal en otro país para excluir ausencias esporádicas: explica cuál de esas cuestiones respalda cada pasaje. No conviertas la prueba o el resultado de un caso concreto en una regla general salvo que el pasaje formule expresamente doctrina. Si se preguntan pruebas aceptadas por un tribunal, distingue lo que valoró la instancia de lo que confirmó o estableció directamente ese tribunal. En materia de ausencias esporádicas, no uses la intención de retorno como criterio sin comprobar si el tribunal la adopta o, por el contrario, la rechaza expresamente. El campo limits contiene solo carencias reales de evidencia o alcance, no conclusiones ni repeticiones de la respuesta. No predigas el caso del usuario ni uses conocimiento externo. Si la recuperación no aporta evidencia suficiente, responde parcial, pregunta o abstención; limita el diagnóstico a esta búsqueda y no concluyas que el corpus carece de documentos.' +
      authorityInstruction +
      retrievalHints(question) +
      '\n\nPregunta del usuario:\n' +
      question;
    const input = {
      model: this.model,
      storeName: this.options.storeName,
      requestId: context.requestId,
      metadataFilter,
      prompt,
    };
    const interactions = [await this.options.interact(input, context.signal)];
    const evaluate = (interaction: Interaction) => {
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
      return { draft, citationCandidates, verified };
    };
    let evaluated = evaluate(interactions[0]);
    if (
      ['completa', 'parcial'].includes(evaluated.draft.status) &&
      evaluated.draft.answer &&
      !evaluated.verified.length &&
      !context.signal.aborted
    ) {
      try {
        const retryInteraction = await this.options.interact(
          {
            ...input,
            prompt:
              prompt +
              '\n\nEste es el segundo y último intento porque el anterior no produjo una cita verificable. Usa File Search y copia en la anotación un pasaje literal con página y metadatos del documento; si no puedes citarlo, abstente.',
          },
          context.signal
        );
        interactions.push(retryInteraction);
        evaluated = evaluate(retryInteraction);
      } catch {
        // Conserva la primera salida y su coste si el reintento no puede evaluarse.
      }
    }
    const { draft, citationCandidates, verified } = evaluated;
    const attemptsUsage = interactions.map(usage);
    const cost = marginalCost(this.model, {
      inputTokens: attemptsUsage.reduce((total, item) => total + item.inputTokens, 0),
      outputTokens: attemptsUsage.reduce((total, item) => total + item.outputTokens, 0),
      retrievedDocumentTokens: attemptsUsage.reduce(
        (total, item) => total + item.retrievedDocumentTokens,
        0
      ),
      complete: attemptsUsage.every((item) => item.complete),
    });
    if (['completa', 'parcial'].includes(draft.status) && draft.answer && !verified.length) {
      return {
        strategy: this.id,
        status: 'error',
        text: '',
        sources: [],
        limits: [
          citationCandidates.length
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
