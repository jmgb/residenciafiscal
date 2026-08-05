import { ChatDiagnosticError, supabaseDiagnostic } from './chat-diagnostics';
import type {
  ComparisonReport,
  ConversationTurn,
  HistoryStrategyId,
  StrategySource,
} from './contracts';

export interface RpcError {
  message: string;
  code?: string | null;
  status?: number | null;
}

export interface SupabaseRpcClient {
  rpc(
    functionName: string,
    parameters: Record<string, unknown>
  ): PromiseLike<{ data: unknown; error: RpcError | null }>;
}

const supabaseFailure = (operation: string, error: RpcError | null, invalidResponse = false) =>
  new ChatDiagnosticError(
    'Supabase no disponible',
    invalidResponse
      ? { dependency: 'supabase', operation, kind: 'invalid_response' }
      : supabaseDiagnostic(operation, error)
  );

export interface ChatRequestInput {
  requestId: string;
  conversationId: string;
  userMessageId: string;
  countryPath: string;
  question: string;
}

export interface ChatExperimentContext {
  experiment_version: string;
  deployed_commit: string;
  comparison_schema_version: ComparisonReport['schema_version'];
  structured_corpus_version: string;
  structured_prompt_version: string;
  file_search_store: string;
  file_search_prompt_version: string;
}

interface ChatCompletionInput {
  requestId: string;
  actualMicrousd: number;
  actualComplete: boolean;
  report: ComparisonReport;
}

interface ChatHistoryInput {
  conversationId: string;
  turnLimit: number;
}

export interface EditorialTurnInput {
  conversationId: string;
  userMessageId: string;
  countryPath: string;
  question: string;
  content: string;
  model: string;
  sources: StrategySource[];
}

const HISTORY_STRATEGY_IDS: readonly HistoryStrategyId[] = [
  'current_structured',
  'gemini_file_search',
  'editorial',
];

/**
 * Acepta solo turnos con la forma esperada y descarta el resto en silencio: un
 * historial parcial sigue siendo contexto útil, y aquí no hay nada que el usuario
 * pueda corregir.
 */
const conversationTurns = (value: unknown): ConversationTurn[] => {
  if (!Array.isArray(value)) return [];
  const turns: ConversationTurn[] = [];
  for (const item of value) {
    if (!item || typeof item !== 'object') continue;
    const candidate = item as { question?: unknown; answers?: unknown };
    if (typeof candidate.question !== 'string' || !candidate.question.trim()) continue;
    const answers = Array.isArray(candidate.answers) ? candidate.answers : [];
    turns.push({
      question: candidate.question,
      answers: answers.flatMap((answer) => {
        if (!answer || typeof answer !== 'object') return [];
        const { strategy, content } = answer as { strategy?: unknown; content?: unknown };
        if (typeof content !== 'string' || !content) return [];
        if (!HISTORY_STRATEGY_IDS.includes(strategy as HistoryStrategyId)) return [];
        return [{ strategy: strategy as HistoryStrategyId, content }];
      }),
    });
  }
  return turns;
};

interface ChatFailureInput {
  requestId: string;
  status: 'failed' | 'timed_out';
  failureCode: 'comparison_error' | 'timeout' | 'aborted' | 'unknown';
}

export type ChatVoteVerdict = 'a' | 'b' | 'c' | 'tie' | 'both_bad';
export type ChatVoteReason =
  | 'better_grounding'
  | 'clearer'
  | 'more_complete'
  | 'better_limits'
  | 'no_preference'
  | 'both_inadequate';

export interface ChatVoteInput {
  requestId: string;
  verdict: ChatVoteVerdict;
  reason: ChatVoteReason;
}

interface RequestRecordResult {
  request_id: string;
  created: boolean;
}

function isRequestRecordResult(value: unknown): value is RequestRecordResult {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<RequestRecordResult>;
  return typeof candidate.request_id === 'string' && candidate.request_id.length > 0;
}

const answerForPersistence = (answer: ComparisonReport['answers'][number]) => ({
  strategy: answer.strategy,
  status: answer.status,
  content: answer.text,
  model: answer.model,
  reasoning_effort: answer.reasoning_effort,
  latency_ms: answer.latency_ms,
  limits: answer.limits,
  sources: answer.sources,
  claims: answer.claims ?? [],
  // La clave se OMITE cuando no hay diagnóstico. Mandarla como `null` llega a Postgres
  // como jsonb 'null' —no como NULL de SQL—, así que `answer->'diagnostics'` no es NULL
  // y `chat_messages_diagnostics_object_check` rechaza la fila entera.
  ...(answer.diagnostics ? { diagnostics: answer.diagnostics } : {}),
  cost_microusd: answer.cost.cost_microusd,
  cost_measurement: answer.cost.measurement,
  pricing_version: answer.cost.pricing_version,
  input_tokens: answer.cost.input_tokens,
  output_tokens: answer.cost.output_tokens,
  retrieved_document_tokens: answer.cost.retrieved_document_tokens,
});

export class SupabaseChatVoteStore {
  constructor(protected readonly client: SupabaseRpcClient) {}

  async vote(input: ChatVoteInput): Promise<boolean> {
    const { data, error } = await this.client.rpc('record_chat_vote', {
      p_request_id: input.requestId,
      p_verdict: input.verdict,
      p_reason: input.reason,
    });
    if (error || typeof data !== 'boolean') {
      throw supabaseFailure('record_chat_vote', error, !error && typeof data !== 'boolean');
    }
    return data;
  }
}

export class SupabaseChatStore extends SupabaseChatVoteStore {
  constructor(
    client: SupabaseRpcClient,
    private readonly experiment: ChatExperimentContext
  ) {
    super(client);
  }

  async record(input: ChatRequestInput): Promise<{ requestId: string }> {
    const { data, error } = await this.client.rpc('create_chat_request', {
      p_request_id: input.requestId,
      p_conversation_id: input.conversationId,
      p_user_message_id: input.userMessageId,
      p_country_path: input.countryPath,
      p_question: input.question,
      p_experiment: this.experiment,
    });
    if (error || !isRequestRecordResult(data)) {
      throw supabaseFailure('create_chat_request', error, !error && !isRequestRecordResult(data));
    }
    return { requestId: data.request_id };
  }

  /**
   * Turnos anteriores de la conversación. Degrada a `[]` ante cualquier fallo: sin
   * contexto la respuesta es peor, pero perder el turno entero por no poder leer
   * el historial sería un 503 evitable.
   */
  async history(input: ChatHistoryInput): Promise<ConversationTurn[]> {
    const { data, error } = await this.client.rpc('read_chat_history', {
      p_conversation_id: input.conversationId,
      p_turn_limit: input.turnLimit,
    });
    if (error) return [];
    return conversationTurns(data);
  }

  /**
   * Registra un turno editorial completo —pregunta y respuesta— como si fuera un
   * turno cualquiera de la conversación, para que `read_chat_history` lo devuelva
   * después. El `request_id` se deriva del identificador del mensaje, así que un
   * reintento del navegador no duplica el turno.
   */
  async recordEditorial(input: EditorialTurnInput): Promise<void> {
    const { requestId } = await this.record({
      requestId: `chat-editorial-${input.userMessageId}`,
      conversationId: input.conversationId,
      userMessageId: input.userMessageId,
      countryPath: input.countryPath,
      question: input.question,
    });
    const { error } = await this.client.rpc('complete_chat_request', {
      p_request_id: requestId,
      p_actual_microusd: 0,
      p_actual_complete: true,
      p_answers: [
        {
          strategy: 'editorial',
          status: 'completa',
          content: input.content,
          model: input.model,
          reasoning_effort: null,
          latency_ms: 0,
          limits: [],
          sources: input.sources,
          claims: [],
          // Cero real: no hubo llamada a ningún proveedor, así que la medición es
          // exacta y no debe presentarse como estimada ni como no disponible.
          cost_microusd: 0,
          cost_measurement: 'ACTUAL',
          pricing_version: 'editorial',
          input_tokens: 0,
          output_tokens: 0,
          retrieved_document_tokens: 0,
        },
      ],
    });
    if (error) throw supabaseFailure('complete_chat_request', error);
  }

  async complete(input: ChatCompletionInput): Promise<void> {
    const { error } = await this.client.rpc('complete_chat_request', {
      p_request_id: input.requestId,
      p_actual_microusd: input.actualMicrousd,
      p_actual_complete: input.actualComplete,
      p_answers: input.report.answers.map(answerForPersistence),
    });
    if (error) throw supabaseFailure('complete_chat_request', error);
  }

  async fail(input: ChatFailureInput): Promise<void> {
    const { error } = await this.client.rpc('fail_chat_request', {
      p_request_id: input.requestId,
      p_status: input.status,
      p_failure_code: input.failureCode,
    });
    if (error) throw supabaseFailure('fail_chat_request', error);
  }
}
