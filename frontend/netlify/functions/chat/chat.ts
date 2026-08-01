/** Entrada HTTP de la Function Netlify V1. */

import { createProductionDependencies } from './composition';
import type { ComparisonReport } from './contracts';
import type { ChatReservationInput } from './supabase-chat-store';

const MAX_REQUEST_BYTES = 200_000;
const MAX_MESSAGES = 20;
const MAX_MESSAGE_CHARS = 500;

export interface BudgetReservation {
  allowed: boolean;
  reservationMicrousd: number;
}

export interface ChatFunctionDependencies {
  enabled: boolean;
  reserveBudget(input: ChatReservationInput): Promise<BudgetReservation>;
  compare(question: string, requestId: string, signal: AbortSignal): Promise<ComparisonReport>;
  failBudget(input: {
    requestId: string;
    status: 'failed' | 'timed_out';
    failureCode: 'comparison_error' | 'timeout' | 'aborted' | 'unknown';
  }): Promise<void>;
  reconcileBudget(input: {
    requestId: string;
    reservationMicrousd: number;
    actualMicrousd: number;
    actualComplete: boolean;
    report: ComparisonReport;
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

const jsonError = (status: number, message: string) =>
  Response.json({ error: message }, { status, headers: { 'cache-control': 'no-store' } });

const validIdentifier = (value: unknown): value is string =>
  typeof value === 'string' && value.length >= 1 && value.length <= 128 && /^[\w-]+$/.test(value);

const validCountryPath = (value: unknown): value is string =>
  typeof value === 'string' && /^\/[a-z0-9-]{1,63}$/.test(value);

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
        limits: answer.limits,
        cost: answer.cost,
        model: answer.model,
        latency_ms: answer.latency_ms,
      })
    );
  }
  events.push(event('done', {}));
  return events.join('');
};

export const createChatHandler =
  (dependencies: ChatFunctionDependencies) =>
  async (request: Request): Promise<Response> => {
    if (request.method !== 'POST') return jsonError(405, 'Método no permitido');
    if (!dependencies.enabled) return jsonError(503, 'Chat no habilitado');
    const parsed = await parseQuestion(request);
    if (!parsed) return jsonError(400, 'Petición inválida');

    const requestId = `chat-${crypto.randomUUID()}`;
    let reservation: BudgetReservation;
    try {
      reservation = await dependencies.reserveBudget({
        requestId,
        conversationId: parsed.conversationId,
        userMessageId: parsed.userMessageId,
        countryPath: parsed.countryPath,
        question: parsed.question,
      });
    } catch {
      return jsonError(503, 'Control de presupuesto no disponible');
    }
    if (!reservation.allowed) return jsonError(429, 'Presupuesto diario agotado');

    let report: ComparisonReport;
    try {
      report = await dependencies.compare(parsed.question, requestId, request.signal);
    } catch {
      // La reserva se conserva: ante uso de proveedor desconocido es más seguro
      // agotar antes el techo que liberar gasto que quizá ya se haya producido.
      try {
        await dependencies.failBudget({
          requestId,
          status: request.signal.aborted ? 'timed_out' : 'failed',
          failureCode: request.signal.aborted ? 'aborted' : 'comparison_error',
        });
      } catch {
        // Mantener la respuesta cerrada si también falla el registro del fallo.
      }
      return jsonError(503, 'Comparación no disponible');
    }
    const actualMicrousd = report.answers.reduce(
      (total, answer) => total + (answer.cost.cost_microusd ?? 0),
      0
    );
    const actualComplete = report.answers.every((answer) => answer.cost.measurement === 'ACTUAL');
    try {
      await dependencies.reconcileBudget({
        requestId,
        reservationMicrousd: reservation.reservationMicrousd,
        actualMicrousd,
        actualComplete,
        report,
      });
    } catch {
      return jsonError(503, 'Registro de coste no disponible');
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
