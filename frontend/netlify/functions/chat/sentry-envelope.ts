import { sanitizeChatDiagnostic } from './chat-diagnostics';
import {
  CHAT_OBSERVABILITY_SCHEMA_VERSION,
  type ChatFailureEvent,
  sanitizeErrorName,
} from './observability-contracts';

export interface SentryDsnParts {
  endpoint: string;
  publicKey: string;
}

export interface SyntheticFailureEvent {
  eventName: 'chat_request_failed' | 'chat_strategy_failed';
  requestId: string;
  failureCode: string;
  qualifierKey: 'stage' | 'strategy';
  qualifierValue: string;
  fingerprint: string[];
  errorName?: string;
  latencyMs?: number;
  tags?: Record<string, string>;
  errorContext?: ChatFailureEvent['errorContext'];
}

interface SentryEnvelopeOptions {
  environment: string;
  release?: string;
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

export const buildSentryEnvelope = (
  options: SentryEnvelopeOptions,
  event: SyntheticFailureEvent
): string => {
  const eventId = crypto.randomUUID().replace(/-/g, '');
  const errorContext = event.errorContext ? sanitizeChatDiagnostic(event.errorContext) : undefined;
  const payload = {
    event_id: eventId,
    timestamp: Date.now() / 1000,
    platform: 'node',
    level: 'error',
    logger: 'chat',
    environment: options.environment,
    ...(options.release ? { release: options.release } : {}),
    message: {
      formatted: `${event.eventName}: ${event.failureCode} (${event.qualifierValue})`,
    },
    fingerprint: event.fingerprint,
    tags: {
      schema_version: CHAT_OBSERVABILITY_SCHEMA_VERSION,
      service: 'residencia-fiscal',
      component: 'netlify-function',
      failure_code: event.failureCode,
      [event.qualifierKey]: event.qualifierValue,
      error_name: sanitizeErrorName(event.errorName),
      ...(errorContext
        ? {
            dependency: errorContext.dependency,
            operation: errorContext.operation,
            error_kind: errorContext.kind,
            ...(errorContext.code ? { error_code: errorContext.code } : {}),
            ...(errorContext.status !== undefined
              ? { provider_status: String(errorContext.status) }
              : {}),
            ...(errorContext.retryable !== undefined
              ? { retryable: String(errorContext.retryable) }
              : {}),
          }
        : {}),
      ...event.tags,
    },
    extra: {
      request_id: event.requestId,
      ...(event.latencyMs !== undefined ? { latency_ms: event.latencyMs } : {}),
      ...(errorContext ? { error_context: errorContext } : {}),
    },
  };
  return [
    JSON.stringify({ event_id: eventId, sent_at: new Date().toISOString() }),
    JSON.stringify({ type: 'event' }),
    JSON.stringify(payload),
  ].join('\n');
};
