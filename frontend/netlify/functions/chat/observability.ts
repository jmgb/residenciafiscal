/**
 * Observabilidad de la Function del chat.
 *
 * Invariante de privacidad: una pregunta del chat es dato fiscal. A Sentry solo
 * viaja un evento **sintético** —código de fallo, etapa, identificador de
 * petición y nombre de clase del error—, nunca la pregunta, la respuesta ni el
 * mensaje de la excepción del proveedor, que puede traer el prompt incrustado.
 *
 * Por eso el envelope se construye a mano en lugar de usar `@sentry/node`: el
 * SDK captura breadcrumbs de consola y contexto del runtime por defecto, y esta
 * Function loguea eventos estructurados por consola. Lo que sale hacia Sentry es
 * exactamente lo que construye `sentry-envelope.ts`.
 */

import { sanitizeChatDiagnostic } from './chat-diagnostics';
import {
  CHAT_OBSERVABILITY_SCHEMA_VERSION,
  type ChatCostEvent,
  type ChatFailureEvent,
  type ChatObservability,
  type ChatStrategyFailureEvent,
  sanitizeErrorName,
} from './observability-contracts';
import {
  buildSentryEnvelope,
  parseSentryDsn,
  type SentryDsnParts,
  type SyntheticFailureEvent,
} from './sentry-envelope';

export type {
  ChatCostEvent,
  ChatFailureEvent,
  ChatObservability,
  ChatStrategyFailureEvent,
} from './observability-contracts';
export { parseSentryDsn } from './sentry-envelope';

/** Emite los eventos estructurados que ya consumen los logs de Netlify. */
export class ConsoleChatObservability implements ChatObservability {
  async recordFailure(event: ChatFailureEvent): Promise<void> {
    console.error(
      JSON.stringify({
        schema_version: CHAT_OBSERVABILITY_SCHEMA_VERSION,
        event: 'chat_request_failed',
        request_id: event.requestId,
        failure_code: event.failureCode,
        stage: event.stage,
        ...(event.status ? { status: event.status } : {}),
        ...(event.errorName ? { error_name: sanitizeErrorName(event.errorName) } : {}),
        ...(event.latencyMs !== undefined ? { latency_ms: event.latencyMs } : {}),
        ...(event.errorContext
          ? { error_context: sanitizeChatDiagnostic(event.errorContext) }
          : {}),
      })
    );
  }

  async recordStrategyFailure(event: ChatStrategyFailureEvent): Promise<void> {
    console.error(
      JSON.stringify({
        schema_version: CHAT_OBSERVABILITY_SCHEMA_VERSION,
        event: 'chat_strategy_failed',
        request_id: event.requestId,
        strategy: event.strategy,
        failure_code: event.failureCode,
        error_name: sanitizeErrorName(event.errorName),
        latency_ms: event.latencyMs,
        ...(event.errorContext
          ? { error_context: sanitizeChatDiagnostic(event.errorContext) }
          : {}),
      })
    );
  }

  async recordCost(event: ChatCostEvent): Promise<void> {
    console.info(
      JSON.stringify({
        schema_version: CHAT_OBSERVABILITY_SCHEMA_VERSION,
        event: 'chat_cost_reconciled',
        request_id: event.requestId,
        request_status: 'completed',
        actual_microusd: event.actualMicrousd,
        actual_complete: event.actualComplete,
        cost_measurement_complete: event.actualComplete,
        authority_intent: event.authorityIntent,
        timings_ms: event.timingsMs,
        strategies: event.strategies,
      })
    );
  }
}

export interface SentryChatObservabilityOptions {
  dsn: string;
  environment: string;
  release?: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
  inner: ChatObservability;
}

/**
 * Decora otro sink añadiendo el envío a Sentry. El coste no se envía: no es un
 * error y su canal es el resumen diario sobre el ledger de Supabase.
 */
export class SentryChatObservability implements ChatObservability {
  private readonly parts: SentryDsnParts | null;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(private readonly options: SentryChatObservabilityOptions) {
    this.parts = parseSentryDsn(options.dsn);
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.timeoutMs = options.timeoutMs ?? 2_000;
  }

  private async send(event: SyntheticFailureEvent): Promise<void> {
    if (!this.parts) return;
    try {
      await this.fetchImpl(this.parts.endpoint, {
        method: 'POST',
        headers: {
          'content-type': 'application/x-sentry-envelope',
          'X-Sentry-Auth': `Sentry sentry_version=7, sentry_key=${this.parts.publicKey}, sentry_client=residenciafiscal-chat/1.0`,
        },
        body: buildSentryEnvelope(this.options, event),
        signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch {
      // Observar no puede tumbar el chat: el fallo ya quedó en el log estructurado.
    }
  }

  async recordFailure(event: ChatFailureEvent): Promise<void> {
    await this.options.inner.recordFailure(event);
    await this.send({
      eventName: 'chat_request_failed',
      requestId: event.requestId,
      failureCode: event.failureCode,
      qualifierKey: 'stage',
      qualifierValue: event.stage,
      fingerprint: ['chat_request_failed', event.failureCode, event.stage],
      errorName: event.errorName,
      latencyMs: event.latencyMs,
      errorContext: event.errorContext,
      tags: event.status ? { status: event.status } : undefined,
    });
  }

  async recordStrategyFailure(event: ChatStrategyFailureEvent): Promise<void> {
    await this.options.inner.recordStrategyFailure(event);
    await this.send({
      eventName: 'chat_strategy_failed',
      requestId: event.requestId,
      failureCode: event.failureCode,
      qualifierKey: 'strategy',
      qualifierValue: event.strategy,
      fingerprint: ['chat_strategy_failed', event.strategy, event.failureCode],
      errorName: event.errorName,
      latencyMs: event.latencyMs,
      errorContext: event.errorContext,
    });
  }

  async recordCost(event: ChatCostEvent): Promise<void> {
    await this.options.inner.recordCost(event);
  }
}

export const createChatObservability = (
  environment: Record<string, string | undefined>
): ChatObservability => {
  const console = new ConsoleChatObservability();
  const dsn = environment.CHAT_SENTRY_DSN?.trim();
  if (environment.CHAT_SENTRY_ENABLED !== 'true' || !dsn || !parseSentryDsn(dsn)) {
    return console;
  }
  return new SentryChatObservability({
    dsn,
    environment: environment.SENTRY_ENVIRONMENT?.trim() || 'production',
    release:
      environment.SENTRY_RELEASE?.trim() ||
      environment.COMMIT_REF?.trim() ||
      environment.DEPLOY_ID?.trim() ||
      undefined,
    inner: console,
  });
};
