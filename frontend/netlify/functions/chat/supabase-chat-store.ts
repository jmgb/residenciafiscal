import type { ComparisonReport } from './contracts';

interface RpcError {
  message: string;
}

export interface SupabaseRpcClient {
  rpc(
    functionName: string,
    parameters: Record<string, unknown>
  ): PromiseLike<{ data: unknown; error: RpcError | null }>;
}

export interface ChatReservationInput {
  requestId: string;
  conversationId: string;
  userMessageId: string;
  countryPath: string;
  question: string;
}

interface ChatReconciliationInput {
  requestId: string;
  actualMicrousd: number;
  actualComplete: boolean;
  report: ComparisonReport;
}

interface ReservationResult {
  allowed: boolean;
  reservation_microusd: number;
}

function isReservationResult(value: unknown): value is ReservationResult {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<ReservationResult>;
  return (
    typeof candidate.allowed === 'boolean' &&
    Number.isSafeInteger(candidate.reservation_microusd) &&
    Number(candidate.reservation_microusd) >= 0
  );
}

const answerForPersistence = (answer: ComparisonReport['answers'][number]) => ({
  strategy: answer.strategy,
  status: answer.status,
  content: answer.text,
  model: answer.model,
  latency_ms: answer.latency_ms,
  limits: answer.limits,
  sources: answer.sources,
  cost_microusd: answer.cost.cost_microusd,
  cost_measurement: answer.cost.measurement,
  pricing_version: answer.cost.pricing_version,
  input_tokens: answer.cost.input_tokens,
  output_tokens: answer.cost.output_tokens,
  retrieved_document_tokens: answer.cost.retrieved_document_tokens,
});

export class SupabaseChatStore {
  constructor(
    private readonly client: SupabaseRpcClient,
    private readonly limits: { dailyLimitMicrousd: number; reservationMicrousd: number }
  ) {
    if (
      !Number.isSafeInteger(limits.dailyLimitMicrousd) ||
      !Number.isSafeInteger(limits.reservationMicrousd) ||
      limits.dailyLimitMicrousd < 1 ||
      limits.reservationMicrousd < 1 ||
      limits.reservationMicrousd > limits.dailyLimitMicrousd
    ) {
      throw new Error('Los límites del presupuesto deben ser válidos');
    }
  }

  async reserve(input: ChatReservationInput) {
    const { data, error } = await this.client.rpc('reserve_chat_request', {
      p_request_id: input.requestId,
      p_conversation_id: input.conversationId,
      p_user_message_id: input.userMessageId,
      p_country_path: input.countryPath,
      p_question: input.question,
      p_daily_limit_microusd: this.limits.dailyLimitMicrousd,
      p_reservation_microusd: this.limits.reservationMicrousd,
    });
    if (error || !isReservationResult(data)) throw new Error('Supabase no disponible');
    return {
      allowed: data.allowed,
      reservationMicrousd: data.reservation_microusd,
    };
  }

  async reconcile(input: ChatReconciliationInput): Promise<void> {
    const { error } = await this.client.rpc('complete_chat_request', {
      p_request_id: input.requestId,
      p_actual_microusd: input.actualMicrousd,
      p_actual_complete: input.actualComplete,
      p_answers: input.report.answers.map(answerForPersistence),
    });
    if (error) throw new Error('Supabase no disponible');
  }
}
