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
 * exactamente lo que se lee en `buildEnvelope`.
 */

export type ChatFailureStage = 'record' | 'compare' | 'complete';

export interface ChatFailureEvent {
  requestId: string;
  failureCode: string;
  stage: ChatFailureStage;
  status?: 'failed' | 'timed_out';
  /** Nombre de la clase del error. Se sanea antes de salir del proceso. */
  errorName?: string;
}

export interface ChatCostStrategy {
  strategy: string;
  status: string;
  model: string | null;
  reasoning_effort: string | null;
  latency_ms: number;
  cost_microusd: number | null;
  measurement: string;
  input_tokens: number | null;
  output_tokens: number | null;
  retrieved_document_tokens: number | null;
}

export interface ChatCostEvent {
  requestId: string;
  actualMicrousd: number;
  actualComplete: boolean;
  strategies: readonly ChatCostStrategy[];
}

export interface ChatObservability {
  recordFailure(event: ChatFailureEvent): Promise<void>;
  recordCost(event: ChatCostEvent): Promise<void>;
}

export interface SentryDsnParts {
  endpoint: string;
  publicKey: string;
}

export const parseSentryDsn = (dsn: string): SentryDsnParts | null => {
  if (!dsn) return null;
  let url: URL;
  try {
    url = new URL(dsn);
  } catch {
    return null;
  }
  const projectId = url.pathname.replace(/^\/+/, '');
  if (!projectId || !url.username) return null;
  return {
    endpoint: `${url.protocol}//${url.host}/api/${projectId}/envelope/`,
    publicKey: url.username,
  };
};

/**
 * Solo un identificador de clase puede salir como `error_name`. Cualquier otra
 * cosa —un mensaje del proveedor, una URL con credenciales— se descarta entera.
 */
const sanitizeErrorName = (value: string | undefined): string =>
  value && /^[A-Za-z][A-Za-z0-9_]{0,39}$/.test(value) ? value : 'unknown';

/** Emite los eventos estructurados que ya consumen los logs de Netlify. */
export class ConsoleChatObservability implements ChatObservability {
  async recordFailure(event: ChatFailureEvent): Promise<void> {
    console.error(
      JSON.stringify({
        event: 'chat_request_failed',
        request_id: event.requestId,
        failure_code: event.failureCode,
        stage: event.stage,
        ...(event.status ? { status: event.status } : {}),
      })
    );
  }

  async recordCost(event: ChatCostEvent): Promise<void> {
    console.info(
      JSON.stringify({
        event: 'chat_cost_reconciled',
        request_id: event.requestId,
        actual_microusd: event.actualMicrousd,
        actual_complete: event.actualComplete,
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

  private buildEnvelope(event: ChatFailureEvent): string {
    const eventId = crypto.randomUUID().replace(/-/g, '');
    const payload = {
      event_id: eventId,
      timestamp: Date.now() / 1000,
      platform: 'node',
      level: 'error',
      logger: 'chat',
      environment: this.options.environment,
      ...(this.options.release ? { release: this.options.release } : {}),
      message: {
        formatted: `chat_request_failed: ${event.failureCode} (${event.stage})`,
      },
      fingerprint: ['chat_request_failed', event.failureCode, event.stage],
      tags: {
        service: 'residencia-fiscal',
        component: 'netlify-function',
        failure_code: event.failureCode,
        stage: event.stage,
        ...(event.status ? { status: event.status } : {}),
        error_name: sanitizeErrorName(event.errorName),
      },
      extra: { request_id: event.requestId },
    };
    return [
      JSON.stringify({ event_id: eventId, sent_at: new Date().toISOString() }),
      JSON.stringify({ type: 'event' }),
      JSON.stringify(payload),
    ].join('\n');
  }

  async recordFailure(event: ChatFailureEvent): Promise<void> {
    await this.options.inner.recordFailure(event);
    if (!this.parts) return;
    try {
      await this.fetchImpl(this.parts.endpoint, {
        method: 'POST',
        headers: {
          'content-type': 'application/x-sentry-envelope',
          'X-Sentry-Auth': `Sentry sentry_version=7, sentry_key=${this.parts.publicKey}, sentry_client=residenciafiscal-chat/1.0`,
        },
        body: this.buildEnvelope(event),
        signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch {
      // Observar no puede tumbar el chat: el fallo ya quedó en el log estructurado.
    }
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
    release: environment.SENTRY_RELEASE?.trim() || undefined,
    inner: console,
  });
};
