import { getDatabase } from '@netlify/database';
import corpus from '../../../../knowledge/jurisprudencia-v3/retrieval/corpus.json';
import san1071 from '../../../../knowledge/jurisprudencia-v3/verbatim/san-1071-2025.pages.json';
import san1136 from '../../../../knowledge/jurisprudencia-v3/verbatim/san-1136-2016.pages.json';
import san1210 from '../../../../knowledge/jurisprudencia-v3/verbatim/san-1210-2023.pages.json';
import san1226 from '../../../../knowledge/jurisprudencia-v3/verbatim/san-1226-2021.pages.json';
import san1386 from '../../../../knowledge/jurisprudencia-v3/verbatim/san-1386-2017.pages.json';
import { PostgresBudgetLedger, type SqlPool } from './budget-ledger';
import type { ChatFunctionDependencies } from './chat';
import { CurrentStructuredStrategy } from './current-structured-strategy';
import { GeminiFileSearchStrategy } from './file-search-strategy';
import { createGeminiInteraction, createOpenAIWriter } from './provider-adapters';
import { compareStrategiesInParallel } from './runtime';

const artifacts = {
  'san-1071-2025': san1071,
  'san-1136-2016': san1136,
  'san-1210-2023': san1210,
  'san-1226-2021': san1226,
  'san-1386-2017': san1386,
};

const usdToMicrousd = (raw: string | undefined): number | null => {
  if (!raw || !/^\d+(?:\.\d{1,6})?$/.test(raw.trim())) return null;
  const [whole, fraction = ''] = raw.trim().split('.');
  const amount = Number(whole) * 1_000_000 + Number(fraction.padEnd(6, '0'));
  return Number.isSafeInteger(amount) && amount > 0 ? amount : null;
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
  const databaseUrl = environment.NETLIFY_DB_URL?.trim();
  const dailyLimitMicrousd = usdToMicrousd(environment.CHAT_DAILY_BUDGET_USD);
  const reservationMicrousd = usdToMicrousd(environment.CHAT_REQUEST_RESERVATION_USD);
  const deadlineMs = deadline(environment.CHAT_DEADLINE_MS);
  const fileSearchModel = environment.CHAT_FILE_SEARCH_MODEL?.trim() || 'gemini-3.5-flash-lite';
  const enabled = environment.CHAT_COMPARISON_ENABLED === 'true';
  if (
    !enabled ||
    !openAIKey ||
    !geminiKey ||
    !databaseUrl?.startsWith('postgres') ||
    !storeName?.startsWith('fileSearchStores/') ||
    !dailyLimitMicrousd ||
    !reservationMicrousd ||
    reservationMicrousd > dailyLimitMicrousd ||
    !deadlineMs ||
    !['gemini-3.5-flash-lite', 'gemini-3.6-flash'].includes(fileSearchModel)
  ) {
    return {
      enabled: false,
      async reserveBudget() {
        return { allowed: false, reservationMicrousd: 0 };
      },
      async compare() {
        throw new Error('Chat no configurado');
      },
      async reconcileBudget() {},
    };
  }

  const database = getDatabase();
  const ledger = new PostgresBudgetLedger(database.pool as unknown as SqlPool, {
    dailyLimitMicrousd,
    reservationMicrousd,
  });
  const structured = new CurrentStructuredStrategy(corpus, createOpenAIWriter(openAIKey));
  const fileSearch = new GeminiFileSearchStrategy({
    storeName,
    artifacts,
    interact: createGeminiInteraction(geminiKey),
    model: fileSearchModel,
  });

  return {
    enabled: true,
    reserveBudget: (requestId) => ledger.reserve(requestId),
    compare: (question, requestId, signal) =>
      compareStrategiesInParallel({
        question,
        requestId,
        signal,
        deadlineMs,
        strategies: [structured, fileSearch],
      }),
    reconcileBudget: async ({ requestId, actualMicrousd, actualComplete, report }) => {
      await ledger.reconcile({
        requestId,
        actualMicrousd,
        actualComplete,
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
