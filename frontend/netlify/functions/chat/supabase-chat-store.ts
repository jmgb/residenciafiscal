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

export interface ChatRequestInput {
  requestId: string;
  conversationId: string;
  userMessageId: string;
  countryPath: string;
  question: string;
}

interface ChatCompletionInput {
  requestId: string;
  actualMicrousd: number;
  actualComplete: boolean;
  report: ComparisonReport;
}

interface ChatFailureInput {
  requestId: string;
  status: 'failed' | 'timed_out';
  failureCode: 'comparison_error' | 'timeout' | 'aborted' | 'unknown';
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
  constructor(private readonly client: SupabaseRpcClient) {}

  async record(input: ChatRequestInput): Promise<{ requestId: string }> {
    const { data, error } = await this.client.rpc('create_chat_request', {
      p_request_id: input.requestId,
      p_conversation_id: input.conversationId,
      p_user_message_id: input.userMessageId,
      p_country_path: input.countryPath,
      p_question: input.question,
    });
    if (error || !isRequestRecordResult(data)) throw new Error('Supabase no disponible');
    return { requestId: data.request_id };
  }

  async complete(input: ChatCompletionInput): Promise<void> {
    const { error } = await this.client.rpc('complete_chat_request', {
      p_request_id: input.requestId,
      p_actual_microusd: input.actualMicrousd,
      p_actual_complete: input.actualComplete,
      p_answers: input.report.answers.map(answerForPersistence),
    });
    if (error) throw new Error('Supabase no disponible');
  }

  async fail(input: ChatFailureInput): Promise<void> {
    const { error } = await this.client.rpc('fail_chat_request', {
      p_request_id: input.requestId,
      p_status: input.status,
      p_failure_code: input.failureCode,
    });
    if (error) throw new Error('Supabase no disponible');
  }
}
