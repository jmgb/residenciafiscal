import * as Sentry from '@sentry/react';

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

export const initializeSentry = (config: FrontendSentryConfig): boolean => {
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
