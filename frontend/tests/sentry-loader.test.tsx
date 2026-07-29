import { readFileSync } from 'node:fs';
import path from 'node:path';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { initializeSentry, SentryErrorBoundary } from '@/lib/sentry';

const runtimeMock = vi.hoisted(() => ({
  captureReactException: vi.fn(),
  initializeSentryRuntime: vi.fn(() => true),
}));

vi.mock('@/lib/sentry-runtime', () => runtimeMock);

const config = {
  dsn: 'https://public@example.ingest.sentry.io/1',
  enabled: true,
  environment: 'production',
  release: 'residencia-fiscal-frontend@test',
  tracesSampleRate: 0.1,
};

describe('Sentry lazy loader', () => {
  beforeEach(() => {
    runtimeMock.captureReactException.mockClear();
    runtimeMock.initializeSentryRuntime.mockClear();
    runtimeMock.initializeSentryRuntime.mockReturnValue(true);
  });

  it('does not load the runtime when monitoring is disabled', async () => {
    await expect(initializeSentry({ ...config, enabled: false })).resolves.toBe(false);
    expect(runtimeMock.initializeSentryRuntime).not.toHaveBeenCalled();
  });

  it('loads and initializes the runtime on demand', async () => {
    await expect(initializeSentry(config)).resolves.toBe(true);
    expect(runtimeMock.initializeSentryRuntime).toHaveBeenCalledWith(config);
  });

  it('handles runtime failures and can retry initialization', async () => {
    runtimeMock.initializeSentryRuntime.mockImplementationOnce(() => {
      throw new Error('runtime unavailable');
    });

    await expect(initializeSentry(config)).resolves.toBe(false);
    await expect(initializeSentry(config)).resolves.toBe(true);
    expect(runtimeMock.initializeSentryRuntime).toHaveBeenCalledTimes(2);
  });

  it('keeps @sentry/react out of the entrypoint and loader modules', () => {
    const mainSource = readFileSync(path.resolve(process.cwd(), 'src/main.tsx'), 'utf8');
    const loaderSource = readFileSync(path.resolve(process.cwd(), 'src/lib/sentry.tsx'), 'utf8');

    expect(mainSource).not.toContain("from '@sentry/react'");
    expect(loaderSource).not.toContain("from '@sentry/react'");
  });

  it('captures render errors after showing the fallback', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const error = new Error('render failed');
    const BrokenComponent = () => {
      throw error;
    };
    await initializeSentry(config);

    render(
      <SentryErrorBoundary fallback={<p>Fallback visible</p>}>
        <BrokenComponent />
      </SentryErrorBoundary>
    );

    expect(screen.getByText('Fallback visible')).toBeInTheDocument();
    await waitFor(() =>
      expect(runtimeMock.captureReactException).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      )
    );
    consoleError.mockRestore();
  });
});
