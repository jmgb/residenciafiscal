/**
 * Parser puro del protocolo SSE del chat.
 *
 * No conoce `fetch` ni el endpoint. Su única responsabilidad es convertir un
 * stream de bytes ya aceptado por el transporte en `ChatChunk` verificados.
 */
import { areChatSourcesV2 } from '@/lib/chat-source';
import type {
  ChatAnswerStatus,
  ChatChunk,
  ChatMarginalCost,
  ChatStrategyClaim,
  ChatStrategyFailureCode,
  ChatStrategyId,
  ChatStrategySource,
} from '@/types/chat';

export class ChatEngineError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly retryable = false
  ) {
    super(message);
    this.name = 'ChatEngineError';
  }
}

interface ParsedSseEvent {
  name: string;
  data: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parseEventBlock(block: string): ParsedSseEvent | null {
  let name = 'message';
  const dataLines: string[] = [];

  for (const line of block.split('\n')) {
    if (!line || line.startsWith(':')) continue;
    if (line.startsWith('event:')) {
      name = line.slice('event:'.length).trim();
      continue;
    }
    if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).trimStart());
  }

  if (dataLines.length === 0) return null;

  try {
    return { name, data: JSON.parse(dataLines.join('\n')) };
  } catch {
    throw new ChatEngineError('El servidor envió un evento JSON inválido.', 'invalid_event');
  }
}

const STRATEGIES = ['current_structured', 'gemini_file_search'] as const;
const ANSWER_STATUSES = ['completa', 'parcial', 'pregunta', 'abstención', 'error'] as const;
const FAILURE_CODES = [
  'timeout',
  'exception',
  'strategy_contract',
  'citation_verification',
  'evidence_validation',
] as const;

function isStrategy(value: unknown): value is ChatStrategyId {
  return STRATEGIES.some((strategy) => strategy === value);
}

function isAnswerStatus(value: unknown): value is ChatAnswerStatus {
  return ANSWER_STATUSES.some((status) => status === value);
}

function isFailureCode(value: unknown): value is ChatStrategyFailureCode {
  return FAILURE_CODES.some((code) => code === value);
}

function parseToken(data: unknown, comparative: boolean): Extract<ChatChunk, { type: 'token' }> {
  if (!isRecord(data) || typeof data.text !== 'string') {
    throw new ChatEngineError('El servidor envió un token inválido.', 'invalid_event');
  }
  if (comparative && !isStrategy(data.strategy)) {
    throw new ChatEngineError('El servidor envió un token sin estrategia.', 'invalid_event');
  }
  return comparative
    ? { type: 'token', strategy: data.strategy as ChatStrategyId, text: data.text }
    : { type: 'token', text: data.text };
}

function parseLegacySources(data: unknown): ChatChunk {
  if (!isRecord(data) || !areChatSourcesV2(data.sources)) {
    throw new ChatEngineError(
      'El servidor envió fuentes sin trazabilidad válida.',
      'invalid_sources'
    );
  }
  return { type: 'sources', sources: data.sources };
}

function parseStrategySource(value: unknown): ChatStrategySource | null {
  if (!isRecord(value)) return null;
  if (
    !isStrategy(value.strategy) ||
    typeof value.judgment_id !== 'string' ||
    !value.judgment_id ||
    !Number.isSafeInteger(value.page) ||
    (value.page as number) < 1 ||
    typeof value.source_sha256 !== 'string' ||
    !/^[0-9a-f]{64}$/i.test(value.source_sha256) ||
    typeof value.quote !== 'string' ||
    !value.quote.trim() ||
    value.verification !== 'EXACT'
  ) {
    return null;
  }
  return {
    strategy: value.strategy,
    judgmentId: value.judgment_id,
    page: value.page as number,
    sourceSha256: value.source_sha256,
    quote: value.quote,
    verification: value.verification,
  };
}

function parseStrategySources(data: unknown): Extract<ChatChunk, { type: 'strategy_sources' }> {
  if (!isRecord(data) || !isStrategy(data.strategy) || !Array.isArray(data.sources)) {
    throw new ChatEngineError(
      'El servidor envió fuentes comparativas inválidas.',
      'invalid_sources'
    );
  }
  const sources = data.sources.map(parseStrategySource);
  if (sources.some((source) => source === null)) {
    throw new ChatEngineError(
      'El servidor envió fuentes comparativas inválidas.',
      'invalid_sources'
    );
  }
  const valid = sources as ChatStrategySource[];
  if (valid.some((source) => source.strategy !== data.strategy)) {
    throw new ChatEngineError('El servidor mezcló fuentes de dos estrategias.', 'invalid_sources');
  }
  return { type: 'strategy_sources', strategy: data.strategy, sources: valid };
}

function parseAnswerStart(data: unknown): Extract<ChatChunk, { type: 'answer_start' }> {
  if (!isRecord(data) || !isStrategy(data.strategy) || Object.keys(data).length !== 1) {
    throw new ChatEngineError('El servidor inició una respuesta inválida.', 'invalid_event');
  }
  return { type: 'answer_start', strategy: data.strategy };
}

function parseCost(value: unknown): ChatMarginalCost | null {
  if (!isRecord(value)) return null;
  const unavailable = value.measurement === 'UNAVAILABLE';
  if (
    value.currency !== 'USD' ||
    (unavailable
      ? value.amount_usd !== null ||
        value.cost_microusd !== null ||
        value.input_tokens !== null ||
        value.output_tokens !== null ||
        value.retrieved_document_tokens !== null
      : typeof value.amount_usd !== 'string' ||
        !/^\d+\.\d{6}$/.test(value.amount_usd) ||
        !Number.isSafeInteger(value.cost_microusd) ||
        (value.cost_microusd as number) < 0 ||
        (value.measurement !== 'ACTUAL' && value.measurement !== 'ESTIMATED') ||
        !Number.isSafeInteger(value.input_tokens) ||
        (value.input_tokens as number) < 0 ||
        !Number.isSafeInteger(value.output_tokens) ||
        (value.output_tokens as number) < 0 ||
        !Number.isSafeInteger(value.retrieved_document_tokens) ||
        (value.retrieved_document_tokens as number) < 0) ||
    value.scope !== 'REQUEST_MARGINAL' ||
    typeof value.pricing_version !== 'string' ||
    !value.pricing_version ||
    value.excludes_corpus_preparation !== true
  ) {
    return null;
  }
  if (!unavailable) {
    const amountMicrousd = Number((value.amount_usd as string).replace('.', ''));
    if (!Number.isSafeInteger(amountMicrousd) || amountMicrousd !== value.cost_microusd)
      return null;
  }
  return {
    currency: 'USD',
    amountUsd: value.amount_usd as string | null,
    costMicrousd: value.cost_microusd as number | null,
    measurement: value.measurement as ChatMarginalCost['measurement'],
    scope: 'REQUEST_MARGINAL',
    pricingVersion: value.pricing_version,
    inputTokens: value.input_tokens as number | null,
    outputTokens: value.output_tokens as number | null,
    retrievedDocumentTokens: value.retrieved_document_tokens as number | null,
    excludesCorpusPreparation: true,
  };
}

function parseAnswerDone(data: unknown): Extract<ChatChunk, { type: 'answer_done' }> {
  if (
    !isRecord(data) ||
    !isStrategy(data.strategy) ||
    !isAnswerStatus(data.status) ||
    (data.failure_code !== undefined &&
      data.failure_code !== null &&
      !isFailureCode(data.failure_code)) ||
    (data.claims !== undefined && !Array.isArray(data.claims)) ||
    !Array.isArray(data.limits) ||
    !data.limits.every((limit) => typeof limit === 'string') ||
    typeof data.model !== 'string' ||
    !data.model ||
    !Number.isSafeInteger(data.latency_ms) ||
    (data.latency_ms as number) < 0
  ) {
    throw new ChatEngineError('El servidor terminó una respuesta inválida.', 'invalid_event');
  }
  const cost = parseCost(data.cost);
  if (!cost) {
    throw new ChatEngineError('El servidor envió un coste inválido.', 'invalid_event');
  }
  const claims = ((data.claims ?? []) as unknown[]).map((claim): ChatStrategyClaim | null => {
    if (
      !isRecord(claim) ||
      typeof claim.text !== 'string' ||
      !claim.text.trim() ||
      !Array.isArray(claim.source_indexes) ||
      !claim.source_indexes.every(
        (index) => Number.isSafeInteger(index) && (index as number) >= 1
      ) ||
      new Set(claim.source_indexes).size !== claim.source_indexes.length
    ) {
      return null;
    }
    return {
      text: claim.text.trim(),
      sourceIndexes: claim.source_indexes as number[],
    };
  });
  if (claims.some((claim) => claim === null)) {
    throw new ChatEngineError('El servidor envió afirmaciones inválidas.', 'invalid_event');
  }
  return {
    type: 'answer_done',
    strategy: data.strategy,
    status: data.status,
    ...(data.failure_code ? { failureCode: data.failure_code } : {}),
    ...(data.claims !== undefined ? { claims: claims as ChatStrategyClaim[] } : {}),
    limits: data.limits,
    cost,
    model: data.model,
    latencyMs: data.latency_ms as number,
  };
}

function parseServerError(data: unknown): ChatEngineError {
  if (
    !isRecord(data) ||
    typeof data.code !== 'string' ||
    !data.code ||
    typeof data.message !== 'string' ||
    !data.message ||
    (data.retryable !== undefined && typeof data.retryable !== 'boolean')
  ) {
    return new ChatEngineError('El servidor envió un error inválido.', 'invalid_event');
  }
  return new ChatEngineError(data.message, data.code, data.retryable ?? false);
}

function parseDone(data: unknown): ChatChunk {
  if (!isRecord(data) || Array.isArray(data)) {
    throw new ChatEngineError('El servidor envió un terminal inválido.', 'invalid_event');
  }
  const keys = Object.keys(data);
  if (keys.length === 0) return { type: 'done' };
  if (
    keys.length !== 1 ||
    typeof data.request_id !== 'string' ||
    !/^chat-[\w-]{1,123}$/.test(data.request_id)
  ) {
    throw new ChatEngineError('El servidor envió un terminal inválido.', 'invalid_event');
  }
  return { type: 'done', requestId: data.request_id };
}

function normalizeLineEndings(value: string): string {
  return value.replace(/\r\n/g, '\n');
}

export async function* parseChatEventStream(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<ChatChunk> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  let terminalSeen = false;
  let comparative = false;
  let activeStrategy: ChatStrategyId | null = null;
  const completedStrategies = new Set<ChatStrategyId>();
  let lastStrategyIndex = -1;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        pending += decoder.decode();
        break;
      }
      pending = normalizeLineEndings(pending + decoder.decode(value, { stream: true }));

      let boundary = pending.indexOf('\n\n');
      while (boundary !== -1) {
        const block = pending.slice(0, boundary);
        pending = pending.slice(boundary + 2);
        boundary = pending.indexOf('\n\n');

        const event = parseEventBlock(block);
        if (!event) continue;
        if (terminalSeen) {
          throw new ChatEngineError(
            'El servidor envió datos después del terminal.',
            'event_after_terminal'
          );
        }

        if (event.name === 'answer_start') {
          const chunk = parseAnswerStart(event.data);
          const strategyIndex = STRATEGIES.indexOf(chunk.strategy);
          if (
            activeStrategy ||
            completedStrategies.has(chunk.strategy) ||
            strategyIndex <= lastStrategyIndex
          ) {
            throw new ChatEngineError(
              'El servidor alteró el orden de estrategias.',
              'invalid_event'
            );
          }
          comparative = true;
          activeStrategy = chunk.strategy;
          lastStrategyIndex = strategyIndex;
          yield chunk;
          continue;
        }
        if (event.name === 'token') {
          const chunk = parseToken(event.data, comparative);
          if (comparative && chunk.strategy !== activeStrategy) {
            throw new ChatEngineError(
              'El servidor mezcló tokens de dos estrategias.',
              'invalid_event'
            );
          }
          yield chunk;
          continue;
        }
        if (event.name === 'sources') {
          const chunk = comparative
            ? parseStrategySources(event.data)
            : parseLegacySources(event.data);
          if (
            comparative &&
            chunk.type === 'strategy_sources' &&
            chunk.strategy !== activeStrategy
          ) {
            throw new ChatEngineError(
              'El servidor mezcló fuentes de dos estrategias.',
              'invalid_sources'
            );
          }
          yield chunk;
          continue;
        }
        if (event.name === 'answer_done') {
          if (!comparative || !activeStrategy) {
            throw new ChatEngineError(
              'El servidor terminó una respuesta no iniciada.',
              'invalid_event'
            );
          }
          const chunk = parseAnswerDone(event.data);
          if (chunk.strategy !== activeStrategy) {
            throw new ChatEngineError('El servidor terminó otra estrategia.', 'invalid_event');
          }
          completedStrategies.add(activeStrategy);
          activeStrategy = null;
          yield chunk;
          continue;
        }
        if (event.name === 'done') {
          if (comparative && (activeStrategy || completedStrategies.size === 0)) {
            throw new ChatEngineError('La comparación llegó incompleta.', 'stream_truncated', true);
          }
          terminalSeen = true;
          yield parseDone(event.data);
          continue;
        }
        if (event.name === 'error') {
          terminalSeen = true;
          throw parseServerError(event.data);
        }
        throw new ChatEngineError(
          `El servidor envió un evento desconocido: ${event.name}.`,
          'unexpected_event'
        );
      }
    }
  } catch (error) {
    if (error instanceof ChatEngineError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ChatEngineError(
      'La conexión se interrumpió antes de completar la respuesta.',
      'stream_interrupted',
      true
    );
  } finally {
    reader.releaseLock();
  }

  if (pending.trim() || !terminalSeen) {
    throw new ChatEngineError('La respuesta llegó incompleta.', 'stream_truncated', true);
  }
}
