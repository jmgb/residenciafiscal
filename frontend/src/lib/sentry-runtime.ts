import * as Sentry from '@sentry/react';
import type { ErrorInfo } from 'react';

export interface FrontendSentryConfig {
  dsn?: string;
  enabled: boolean;
  environment: string;
  release: string;
  tracesSampleRate: number;
}

const beforeSend = (event: Sentry.ErrorEvent): Sentry.ErrorEvent => {
  if (event.request) {
    delete event.request.headers;
    delete event.request.cookies;
    delete event.request.data;
  }

  event.tags = {
    ...event.tags,
    service: 'residencia-fiscal',
    component: 'react',
  };
  return event;
};

export const initializeSentryRuntime = (config: FrontendSentryConfig): boolean => {
  if (!config.enabled || !config.dsn) {
    return false;
  }

  Sentry.init({
    dsn: config.dsn,
    environment: config.environment,
    release: config.release,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: config.tracesSampleRate,
    sendDefaultPii: false,
    beforeSend,
  });
  return true;
};

export const captureReactException = (error: unknown, errorInfo: ErrorInfo): void => {
  Sentry.captureReactException(error, errorInfo, {
    mechanism: {
      handled: true,
      type: 'auto.function.react.error_boundary',
    },
  });
};
