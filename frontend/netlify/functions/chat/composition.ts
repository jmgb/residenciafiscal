import { createClient } from '@supabase/supabase-js';
import type { ChatFunctionDependencies } from './chat';
import type { StrategyAnswer } from './contracts';
import { CurrentStructuredStrategy } from './current-structured-strategy';
import { GeminiFileSearchStrategy } from './file-search-strategy';
import {
  authorityMatch,
  type JudicialAuthorityIntent,
  judgmentAuthority,
} from './judicial-authority';
import { createChatObservability } from './observability';
import { productionCorpus, productionVerbatimArtifacts } from './production-corpus';
import { createGeminiInteraction, createOpenAIWriter } from './provider-adapters';
import { compareStrategiesInParallel } from './runtime';
import { SupabaseChatStore, type SupabaseRpcClient } from './supabase-chat-store';

const unique = (values: readonly string[]) => [...new Set(values)].sort();

const safeErrorName = (value: string | null | undefined): string | null => {
  if (!value) return null;
  return /^[A-Za-z][A-Za-z0-9_]{0,39}$/.test(value) ? value : 'unknown';
};

const authorityCounts = (judgmentIds: readonly string[]) => ({
  tribunal_supremo: judgmentIds.filter(
    (judgmentId) => judgmentAuthority(judgmentId) === 'tribunal_supremo'
  ).length,
  audiencia_nacional: judgmentIds.filter(
    (judgmentId) => judgmentAuthority(judgmentId) === 'audiencia_nacional'
  ).length,
  other: judgmentIds.filter((judgmentId) => judgmentAuthority(judgmentId) === 'other').length,
});

const documentTokenAccounting = (
  answer: StrategyAnswer
): 'reported' | 'unavailable' | 'not_applicable' => {
  if (answer.strategy !== 'gemini_file_search') return 'not_applicable';
  if (answer.cost.measurement === 'UNAVAILABLE') return 'unavailable';
  if (answer.sources.length > 0 && answer.cost.retrieved_document_tokens === 0)
    return 'unavailable';
  return 'reported';
};

const observedStrategy = (
  answer: StrategyAnswer,
  authorityIntent: JudicialAuthorityIntent | null
) => {
  const citedJudgmentIds = unique(answer.sources.map((source) => source.judgment_id));
  const judgmentIds = unique(
    answer.diagnostics?.retrieved_judgment_ids.length
      ? answer.diagnostics.retrieved_judgment_ids
      : citedJudgmentIds
  );
  return {
    strategy: answer.strategy,
    status: answer.status,
    model: answer.model,
    reasoning_effort: answer.reasoning_effort,
    latency_ms: answer.latency_ms,
    cost_microusd: answer.cost.cost_microusd,
    measurement: answer.cost.measurement,
    input_tokens: answer.cost.input_tokens,
    output_tokens: answer.cost.output_tokens,
    retrieved_document_tokens: answer.cost.retrieved_document_tokens,
    source_count: answer.sources.length,
    limit_count: answer.limits.length,
    judgment_ids: judgmentIds,
    authority_counts: authorityCounts(citedJudgmentIds),
    authority_match:
      answer.diagnostics?.authority_match ?? authorityMatch(authorityIntent, citedJudgmentIds),
    retrieval_filter: answer.diagnostics?.retrieval_filter ?? null,
    citation_candidates: answer.diagnostics?.citation_candidates ?? answer.sources.length,
    citation_verified: answer.diagnostics?.citation_verified ?? answer.sources.length,
    document_token_accounting: documentTokenAccounting(answer),
    failure_code: answer.diagnostics?.failure_code ?? null,
    error_name: safeErrorName(answer.diagnostics?.error_name),
  };
};

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
  const observability = createChatObservability(environment);
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
      observability,
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
    observability,
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
    completeRequest: async ({
      requestId,
      actualMicrousd,
      actualComplete,
      report,
      authorityIntent,
      timingsMs,
    }) => {
      const persistenceStarted = performance.now();
      await store.complete({
        requestId,
        actualMicrousd,
        actualComplete,
        report,
      });
      const persistenceLatencyMs = Math.round(performance.now() - persistenceStarted);
      await Promise.all(
        report.answers
          .filter((answer) => answer.status === 'error')
          .map((answer) =>
            observability.recordStrategyFailure({
              requestId,
              strategy: answer.strategy,
              failureCode: answer.diagnostics?.failure_code ?? 'unknown',
              errorName: answer.diagnostics?.error_name ?? undefined,
              latencyMs: answer.latency_ms,
            })
          )
      );
      await observability.recordCost({
        requestId,
        actualMicrousd,
        actualComplete,
        authorityIntent,
        timingsMs: {
          record: timingsMs.record,
          compare: timingsMs.compare,
          persistence: persistenceLatencyMs,
          total: timingsMs.beforePersistence + persistenceLatencyMs,
        },
        strategies: report.answers.map((answer) => observedStrategy(answer, authorityIntent)),
      });
    },
  };
};
