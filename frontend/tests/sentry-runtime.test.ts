import { beforeEach, describe, expect, it, vi } from 'vitest';
import { initializeSentryRuntime } from '@/lib/sentry-runtime';

const sentryMock = vi.hoisted(() => ({
  browserTracingIntegration: vi.fn(() => ({ name: 'browser-tracing' })),
  captureReactException: vi.fn(),
  init: vi.fn(),
}));

vi.mock('@sentry/react', () => sentryMock);

describe('Sentry frontend runtime', () => {
  beforeEach(() => {
    sentryMock.browserTracingIntegration.mockClear();
    sentryMock.captureReactException.mockClear();
    sentryMock.init.mockClear();
  });

  it('does not initialize outside an enabled production build', () => {
    expect(
      initializeSentryRuntime({
        dsn: 'https://public@example.ingest.sentry.io/1',
        enabled: false,
        environment: 'development',
        release: 'residencia-fiscal-frontend@test',
        tracesSampleRate: 0.1,
      })
    ).toBe(false);

    expect(sentryMock.init).not.toHaveBeenCalled();
  });

  it('initializes tracing with the configured release and no default PII', () => {
    expect(
      initializeSentryRuntime({
        dsn: 'https://public@example.ingest.sentry.io/1',
        enabled: true,
        environment: 'production',
        release: 'residencia-fiscal-frontend@test',
        tracesSampleRate: 0.2,
      })
    ).toBe(true);

    expect(sentryMock.browserTracingIntegration).toHaveBeenCalledOnce();
    expect(sentryMock.init).toHaveBeenCalledWith(
      expect.objectContaining({
        dsn: 'https://public@example.ingest.sentry.io/1',
        environment: 'production',
        release: 'residencia-fiscal-frontend@test',
        sendDefaultPii: false,
        tracesSampleRate: 0.2,
      })
    );
  });

  it('removes request headers, cookies and bodies before sending an event', () => {
    initializeSentryRuntime({
      dsn: 'https://public@example.ingest.sentry.io/1',
      enabled: true,
      environment: 'production',
      release: 'residencia-fiscal-frontend@test',
      tracesSampleRate: 0.1,
    });

    const options = sentryMock.init.mock.calls[0]?.[0];
    const event = {
      request: {
        url: 'https://residenciafiscal.org/chat',
        method: 'POST',
        headers: { Authorization: 'Bearer secret' },
        cookies: 'session=secret',
        data: { question: 'private legal question' },
      },
    };

    expect(options?.beforeSend(event)).toEqual({
      request: {
        url: 'https://residenciafiscal.org/chat',
        method: 'POST',
      },
      tags: {
        service: 'residencia-fiscal',
        component: 'react',
      },
    });
  });

  it('captures React errors with their component stack and boundary metadata', async () => {
    const { captureReactException } = await import('@/lib/sentry-runtime');
    const error = new Error('render failed');
    const errorInfo = { componentStack: '\n    at BrokenComponent' };

    captureReactException(error, errorInfo);

    expect(sentryMock.captureReactException).toHaveBeenCalledWith(error, errorInfo, {
      mechanism: {
        handled: true,
        type: 'auto.function.react.error_boundary',
      },
    });
  });
});
