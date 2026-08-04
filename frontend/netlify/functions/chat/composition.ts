import { createClient } from '@supabase/supabase-js';
import type { ChatFunctionDependencies } from './chat';
import { sanitizeChatDiagnostic } from './chat-diagnostics';
import type { StrategyAnswer } from './contracts';
import {
  CurrentStructuredStrategy,
  STRUCTURED_PROMPT_VERSION,
} from './current-structured-strategy';
import { FILE_SEARCH_PROMPT_VERSION, GeminiFileSearchStrategy } from './file-search-strategy';
import {
  authorityMatch,
  type JudicialAuthorityIntent,
  judgmentAuthority,
} from './judicial-authority';
import { createChatObservability } from './observability';
import {
  productionCorpus,
  productionCorpusReadiness,
  productionVerbatimArtifacts,
} from './production-corpus';
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
    error_context: answer.diagnostics?.error_context ?? null,
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
  const missingConfiguration = [
    !enabled ? 'CHAT_COMPARISON_ENABLED' : null,
    !openAIKey ? 'OPENAI_API_KEY' : null,
    !geminiKey ? 'GEMINI_API_KEY' : null,
    !supabaseUrl?.startsWith('https://') ? 'SUPABASE_URL' : null,
    !supabaseSecretKey ? 'SUPABASE_SECRET_KEY' : null,
    !storeName?.startsWith('fileSearchStores/') ? 'CHAT_FILE_SEARCH_STORE_NAME' : null,
    !deadlineMs ? 'CHAT_DEADLINE_MS' : null,
    !['gemini-3.5-flash-lite', 'gemini-3.6-flash'].includes(fileSearchModel)
      ? 'CHAT_FILE_SEARCH_MODEL'
      : null,
  ].filter((name): name is string => name !== null);
  const disabledDiagnostic = sanitizeChatDiagnostic({
    dependency: 'configuration',
    operation: 'createProductionDependencies',
    kind: 'chat_disabled',
    missing: missingConfiguration,
  });
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
      disabledDiagnostic,
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
      return { data, error: error ? { message: error.message, code: error.code } : null };
    },
  };
  const store = new SupabaseChatStore(rpcClient, {
    experiment_version: 'ab-2026-08-04-v5',
    deployed_commit:
      environment.COMMIT_REF?.trim() || environment.DEPLOY_ID?.trim() || 'local-development',
    comparison_schema_version: 'residenciafiscal-chat-comparison/1',
    structured_corpus_version: productionCorpusReadiness.sampleId,
    structured_prompt_version: STRUCTURED_PROMPT_VERSION,
    file_search_store: storeName,
    file_search_prompt_version: FILE_SEARCH_PROMPT_VERSION,
  });
  const structured = new CurrentStructuredStrategy(
    productionCorpus,
    createOpenAIWriter(openAIKey),
    productionVerbatimArtifacts
  );
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
              errorContext: answer.diagnostics?.error_context,
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
