import { createClient } from '@supabase/supabase-js';
import type { DeepResearchJobRecord, DeepResearchOutput, DeepResearchStore } from './contracts';

interface RpcClient {
  rpc(
    functionName: string,
    parameters: Record<string, unknown>
  ): PromiseLike<{ data: unknown; error: { message: string } | null }>;
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const outputFromRpc = (value: unknown): DeepResearchOutput | null => {
  if (!isRecord(value)) return null;
  return value as unknown as DeepResearchOutput;
};

const recordFromRpc = (value: unknown): DeepResearchJobRecord | null => {
  if (!isRecord(value) || typeof value.job_id !== 'string') return null;
  if (
    typeof value.conversation_id !== 'string' ||
    (value.comparison_id !== undefined &&
      value.comparison_id !== null &&
      typeof value.comparison_id !== 'string') ||
    typeof value.status !== 'string' ||
    typeof value.stage !== 'string'
  ) {
    return null;
  }
  return {
    jobId: value.job_id,
    conversationId: value.conversation_id,
    comparisonId: typeof value.comparison_id === 'string' ? value.comparison_id : null,
    status: value.status as DeepResearchJobRecord['status'],
    stage: value.stage as DeepResearchJobRecord['stage'],
    result: outputFromRpc(value.result),
    error: typeof value.error === 'string' ? value.error : null,
  };
};

export class SupabaseDeepResearchStore implements DeepResearchStore {
  constructor(private readonly client: RpcClient) {}

  async authorizeConversation(input: {
    conversationId: string;
    countryPath: string;
    conversationAccessHash: string;
  }): Promise<void> {
    const { data, error } = await this.client.rpc('authorize_chat_conversation', {
      p_conversation_id: input.conversationId,
      p_country_path: input.countryPath,
      p_conversation_access_hash: input.conversationAccessHash,
    });
    if (error || data !== true) throw new Error('deep research persistence unavailable');
  }

  async create(input: {
    jobId: string;
    conversationId: string;
    comparisonId: string | null;
    countryPath: string;
    question: string;
    bundleId: string;
  }): Promise<DeepResearchJobRecord> {
    const { data, error } = await this.client.rpc('create_deep_research_job', {
      p_job_id: input.jobId,
      p_conversation_id: input.conversationId,
      p_comparison_id: input.comparisonId,
      p_country_path: input.countryPath,
      p_question: input.question,
      p_bundle_id: input.bundleId,
    });
    const record = recordFromRpc(data);
    if (error || !record) throw new Error('deep research persistence unavailable');
    return record;
  }

  async get(jobId: string, conversationId: string): Promise<DeepResearchJobRecord | null> {
    const { data, error } = await this.client.rpc('get_deep_research_job', {
      p_job_id: jobId,
      p_conversation_id: conversationId,
    });
    if (error) throw new Error('deep research persistence unavailable');
    return recordFromRpc(data);
  }

  async update(input: {
    jobId: string;
    status: DeepResearchJobRecord['status'];
    stage: DeepResearchJobRecord['stage'];
    result: DeepResearchOutput | null;
    error: string | null;
  }): Promise<void> {
    const { error } = await this.client.rpc('update_deep_research_job', {
      p_job_id: input.jobId,
      p_status: input.status,
      p_stage: input.stage,
      p_result: input.result,
      p_error: input.error,
    });
    if (error) throw new Error('deep research persistence unavailable');
  }

  async cancel(jobId: string, conversationId: string): Promise<boolean> {
    const { data, error } = await this.client.rpc('cancel_deep_research_job', {
      p_job_id: jobId,
      p_conversation_id: conversationId,
    });
    if (error || typeof data !== 'boolean')
      throw new Error('deep research persistence unavailable');
    return data;
  }
}

export const createProductionDeepResearchStore = (
  environment: NodeJS.ProcessEnv = process.env
): DeepResearchStore | null => {
  const url = environment.SUPABASE_URL?.trim();
  const secret = environment.SUPABASE_SECRET_KEY?.trim();
  if (!url?.startsWith('https://') || !secret) return null;
  const supabase = createClient(url, secret, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const client: RpcClient = {
    async rpc(functionName, parameters) {
      const { data, error } = await supabase.rpc(functionName, parameters);
      return { data, error: error ? { message: error.message } : null };
    },
  };
  return new SupabaseDeepResearchStore(client);
};
