import { createClient } from '@supabase/supabase-js';
import type { ChatFunctionDependencies } from './chat';
import { CurrentStructuredStrategy } from './current-structured-strategy';
import { GeminiFileSearchStrategy } from './file-search-strategy';
import { productionCorpus, productionVerbatimArtifacts } from './production-corpus';
import { createGeminiInteraction, createOpenAIWriter } from './provider-adapters';
import { compareStrategiesInParallel } from './runtime';
import { SupabaseChatStore, type SupabaseRpcClient } from './supabase-chat-store';

const deadline = (raw: string | undefined) => {
  const value = Number(raw ?? 52_000);
  return Number.isInteger(value) && value >= 1_000 && value <= 55_000 ? value : null;
};

export const createProductionDependencies = (
  environment: NodeJS.ProcessEnv = process.env
): ChatFunctionDependencies => {
  const openAIKey = environment.OPENAI_API_KEY?.trim();
  const geminiKey = environment.GEMINI_API_KEY?.trim();
  const storeName = environment.CHAT_FILE_SEARCH_STORE_NAME?.trim();
  const supabaseUrl = environment.SUPABASE_URL?.trim();
  const supabaseSecretKey = environment.SUPABASE_SECRET_KEY?.trim();
  const deadlineMs = deadline(environment.CHAT_DEADLINE_MS);
  const fileSearchModel = environment.CHAT_FILE_SEARCH_MODEL?.trim() || 'gemini-3.5-flash-lite';
  const enabled = environment.CHAT_COMPARISON_ENABLED === 'true';
  if (
    !enabled ||
    !openAIKey ||
    !geminiKey ||
    !supabaseUrl?.startsWith('https://') ||
    !supabaseSecretKey ||
    !storeName?.startsWith('fileSearchStores/') ||
    !deadlineMs ||
    !['gemini-3.5-flash-lite', 'gemini-3.6-flash'].includes(fileSearchModel)
  ) {
    return {
      enabled: false,
      async recordRequest() {
        throw new Error('Chat no configurado');
      },
      async compare() {
        throw new Error('Chat no configurado');
      },
      async failRequest() {},
      async completeRequest() {},
    };
  }

  const supabase = createClient(supabaseUrl, supabaseSecretKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const rpcClient: SupabaseRpcClient = {
    async rpc(functionName, parameters) {
      const { data, error } = await supabase.rpc(functionName, parameters);
      return { data, error: error ? { message: error.message } : null };
    },
  };
  const store = new SupabaseChatStore(rpcClient);
  const structured = new CurrentStructuredStrategy(productionCorpus, createOpenAIWriter(openAIKey));
  const fileSearch = new GeminiFileSearchStrategy({
    storeName,
    artifacts: productionVerbatimArtifacts,
    interact: createGeminiInteraction(geminiKey),
    model: fileSearchModel,
  });

  return {
    enabled: true,
    recordRequest: (input) => store.record(input),
    compare: (question, requestId, signal) =>
      compareStrategiesInParallel({
        question,
        requestId,
        signal,
        deadlineMs,
        strategies: [structured, fileSearch],
      }),
    failRequest: (input) => store.fail(input),
    completeRequest: async ({ requestId, actualMicrousd, actualComplete, report }) => {
      await store.complete({
        requestId,
        actualMicrousd,
        actualComplete,
        report,
      });
      console.info(
        JSON.stringify({
          event: 'chat_cost_reconciled',
          request_id: requestId,
          actual_microusd: actualMicrousd,
          actual_complete: actualComplete,
          strategies: report.answers.map((answer) => ({
            strategy: answer.strategy,
            status: answer.status,
            model: answer.model,
            latency_ms: answer.latency_ms,
            cost_microusd: answer.cost.cost_microusd,
            measurement: answer.cost.measurement,
            input_tokens: answer.cost.input_tokens,
            output_tokens: answer.cost.output_tokens,
            retrieved_document_tokens: answer.cost.retrieved_document_tokens,
          })),
        })
      );
    },
  };
};
