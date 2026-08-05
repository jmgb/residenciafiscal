/** Entrada HTTP de la Function Netlify V1. */

import { type ChatDiagnostic, diagnosticFromError } from './chat-diagnostics';
import { createProductionDependencies } from './composition';
import type { ComparisonReport, ConversationTurn } from './contracts';
import { type JudicialAuthorityIntent, requestedJudicialAuthority } from './judicial-authority';
import type { ChatObservability } from './observability';
import { validCountryPath, validIdentifier } from './request-identifiers';
import type { ChatRequestInput } from './supabase-chat-store';

const MAX_REQUEST_BYTES = 200_000;
const MAX_MESSAGES = 20;
const MAX_MESSAGE_CHARS = 500;

export interface ChatFunctionDependencies {
  enabled: boolean;
  disabledDiagnostic?: ChatDiagnostic;
  observability: ChatObservability;
  recordRequest(input: ChatRequestInput): Promise<{ requestId: string }>;
  /** Turnos anteriores de la conversación, leídos del ledger; nunca del cuerpo. */
  loadHistory(conversationId: string): Promise<ConversationTurn[]>;
  compare(
    question: string,
    requestId: string,
    signal: AbortSignal,
    history: readonly ConversationTurn[]
  ): Promise<ComparisonReport>;
  failRequest(input: {
    requestId: string;
    status: 'failed' | 'timed_out';
    failureCode: 'comparison_error' | 'timeout' | 'aborted' | 'unknown';
  }): Promise<void>;
  completeRequest(input: {
    requestId: string;
    actualMicrousd: number;
    actualComplete: boolean;
    report: ComparisonReport;
    authorityIntent: JudicialAuthorityIntent | null;
    timingsMs: {
      record: number;
      compare: number;
      beforePersistence: number;
    };
  }): Promise<void>;
}

interface ChatRequestMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ParsedChatRequest {
  question: string;
  conversationId: string;
  userMessageId: string;
  countryPath: string;
}

const jsonError = (status: number, message: string, requestId?: string) =>
  Response.json(
    { error: message },
    {
      status,
      headers: {
        'cache-control': 'no-store',
        ...(requestId ? { 'x-chat-request-id': requestId } : {}),
      },
    }
  );

const parseQuestion = async (request: Request): Promise<ParsedChatRequest | null> => {
  const declaredLength = Number(request.headers.get('content-length'));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) return null;
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return null;
  }
  if (
    !parsed ||
    typeof parsed !== 'object' ||
    !Array.isArray((parsed as { messages?: unknown }).messages)
  ) {
    return null;
  }
  const messages = (parsed as { messages: unknown[] }).messages;
  if (messages.length < 1 || messages.length > MAX_MESSAGES) return null;
  const valid = messages.every(
    (item): item is ChatRequestMessage =>
      Boolean(item) &&
      typeof item === 'object' &&
      ((item as ChatRequestMessage).role === 'user' ||
        (item as ChatRequestMessage).role === 'assistant') &&
      typeof (item as ChatRequestMessage).content === 'string' &&
      (item as ChatRequestMessage).content.length >= 1 &&
      (item as ChatRequestMessage).content.length <= MAX_MESSAGE_CHARS
  );
  if (!valid) return null;
  const latestUser = [...messages]
    .reverse()
    .find((item) => item.role === 'user' && item.content.trim());
  if (!latestUser) return null;
  const bodyIdentifiers = parsed as {
    conversation_id?: unknown;
    country_path?: unknown;
  };
  return {
    question: latestUser.content.trim(),
    conversationId: validIdentifier(bodyIdentifiers.conversation_id)
      ? bodyIdentifiers.conversation_id
      : `conversation-${crypto.randomUUID()}`,
    userMessageId: validIdentifier(latestUser.id)
      ? latestUser.id
      : `message-${crypto.randomUUID()}`,
    countryPath: validCountryPath(bodyIdentifiers.country_path)
      ? bodyIdentifiers.country_path
      : '/espana',
  };
};

const event = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

/**
 * Solo el nombre de la clase del error sale del `catch`. El mensaje del
 * proveedor puede traer el prompt incrustado y nunca se propaga.
 */
const errorNameOf = (error: unknown): string | undefined =>
  error instanceof Error ? error.name : undefined;

export const serializeComparison = (report: ComparisonReport): string => {
  const events: string[] = [];
  for (const answer of report.answers) {
    events.push(event('answer_start', { strategy: answer.strategy }));
    if (answer.text) events.push(event('token', { strategy: answer.strategy, text: answer.text }));
    events.push(event('sources', { strategy: answer.strategy, sources: answer.sources }));
    events.push(
      event('answer_done', {
        strategy: answer.strategy,
        status: answer.status,
        ...(answer.diagnostics?.failure_code
          ? { failure_code: answer.diagnostics.failure_code }
          : {}),
        claims: answer.claims ?? [],
        limits: answer.limits,
        cost: answer.cost,
        model: answer.model,
        latency_ms: answer.latency_ms,
      })
    );
  }
  events.push(event('done', { request_id: report.request_id }));
  return events.join('');
};

export const createChatHandler =
  (dependencies: ChatFunctionDependencies) =>
  async (request: Request): Promise<Response> => {
    const requestStarted = performance.now();
    if (request.method !== 'POST') return jsonError(405, 'Método no permitido');
    const requestId = `chat-${crypto.randomUUID()}`;
    if (!dependencies.enabled) {
      await dependencies.observability.recordFailure({
        requestId,
        failureCode: 'configuration_error',
        stage: 'record',
        errorName: 'ConfigurationError',
        errorContext: dependencies.disabledDiagnostic ?? {
          dependency: 'configuration',
          operation: 'chat_handler',
          kind: 'chat_disabled',
        },
        latencyMs: Math.round(performance.now() - requestStarted),
      });
      return jsonError(503, 'Chat no habilitado', requestId);
    }
    const parsed = await parseQuestion(request);
    if (!parsed) return jsonError(400, 'Petición inválida', requestId);

    const authorityIntent = requestedJudicialAuthority(parsed.question);
    let recordedRequest: { requestId: string };
    const recordStarted = performance.now();
    try {
      recordedRequest = await dependencies.recordRequest({
        requestId,
        conversationId: parsed.conversationId,
        userMessageId: parsed.userMessageId,
        countryPath: parsed.countryPath,
        question: parsed.question,
      });
    } catch (error) {
      await dependencies.observability.recordFailure({
        requestId,
        failureCode: 'record_error',
        stage: 'record',
        errorName: errorNameOf(error),
        latencyMs: Math.round(performance.now() - requestStarted),
        errorContext: diagnosticFromError(error),
      });
      return jsonError(503, 'Registro de conversación no disponible', requestId);
    }
    const recordLatencyMs = Math.round(performance.now() - recordStarted);
    const effectiveRequestId = recordedRequest.requestId;

    // El contexto conversacional es una mejora, no un requisito: si el ledger no
    // devuelve el hilo se responde igual, tratando la pregunta como autosuficiente.
    const history = await dependencies
      .loadHistory(parsed.conversationId)
      .catch(() => [] as ConversationTurn[]);

    let report: ComparisonReport;
    const compareStarted = performance.now();
    try {
      report = await dependencies.compare(
        parsed.question,
        effectiveRequestId,
        request.signal,
        history
      );
    } catch (error) {
      // Solo se registra el diagnóstico estructurado y saneado del proveedor.
      const status = request.signal.aborted ? 'timed_out' : 'failed';
      const failureCode = request.signal.aborted ? 'aborted' : 'comparison_error';
      await dependencies.observability.recordFailure({
        requestId: effectiveRequestId,
        failureCode,
        stage: 'compare',
        status,
        errorName: errorNameOf(error),
        latencyMs: Math.round(performance.now() - requestStarted),
        errorContext: diagnosticFromError(error),
      });
      try {
        await dependencies.failRequest({
          requestId: effectiveRequestId,
          status,
          failureCode,
        });
      } catch {
        // Mantener la respuesta cerrada si también falla el registro del fallo.
      }
      return jsonError(503, 'Comparación no disponible', requestId);
    }
    const compareLatencyMs = Math.round(performance.now() - compareStarted);
    const actualMicrousd = report.answers.reduce(
      (total, answer) => total + (answer.cost.cost_microusd ?? 0),
      0
    );
    const actualComplete = report.answers.every((answer) => answer.cost.measurement === 'ACTUAL');
    try {
      await dependencies.completeRequest({
        requestId: effectiveRequestId,
        actualMicrousd,
        actualComplete,
        report,
        authorityIntent,
        timingsMs: {
          record: recordLatencyMs,
          compare: compareLatencyMs,
          beforePersistence: Math.round(performance.now() - requestStarted),
        },
      });
    } catch (error) {
      await dependencies.observability.recordFailure({
        requestId: effectiveRequestId,
        failureCode: 'completion_error',
        stage: 'complete',
        errorName: errorNameOf(error),
        latencyMs: Math.round(performance.now() - requestStarted),
        errorContext: diagnosticFromError(error),
      });
      // Sin esto la consulta se queda en `processing` indefinidamente: el ledger no
      // distingue una petición viva de una que murió al persistir su coste.
      try {
        await dependencies.failRequest({
          requestId: effectiveRequestId,
          status: 'failed',
          failureCode: 'unknown',
        });
      } catch {
        // Mantener la respuesta cerrada si también falla el registro del fallo.
      }
      return jsonError(503, 'Registro de coste no disponible', requestId);
    }
    return new Response(serializeComparison(report), {
      status: 200,
      headers: {
        'cache-control': 'no-store',
        'content-type': 'text/event-stream; charset=utf-8',
        'x-chat-protocol': '2',
      },
    });
  };

export default createChatHandler(createProductionDependencies());

export const config = {
  path: '/api/chat',
  method: 'POST',
  rateLimit: {
    aggregateBy: ['ip', 'domain'],
    windowSize: 60,
    windowLimit: 5,
  },
};
