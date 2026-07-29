import { Component, type ErrorInfo, type ReactNode } from 'react';
import type { FrontendSentryConfig } from './sentry-runtime';

type SentryRuntime = typeof import('./sentry-runtime');

let runtimePromise: Promise<SentryRuntime> | null = null;
let monitoringEnabled = false;

const loadRuntime = (): Promise<SentryRuntime> => {
  runtimePromise ??= import('./sentry-runtime').catch((error: unknown) => {
    runtimePromise = null;
    throw error;
  });
  return runtimePromise;
};

export const initializeSentry = async (config: FrontendSentryConfig): Promise<boolean> => {
  if (!config.enabled || !config.dsn) {
    monitoringEnabled = false;
    return false;
  }

  try {
    const runtime = await loadRuntime();
    monitoringEnabled = runtime.initializeSentryRuntime(config);
    return monitoringEnabled;
  } catch {
    monitoringEnabled = false;
    return false;
  }
};

interface SentryErrorBoundaryProps {
  children: ReactNode;
  fallback: ReactNode;
}

interface SentryErrorBoundaryState {
  hasError: boolean;
}

export class SentryErrorBoundary extends Component<
  SentryErrorBoundaryProps,
  SentryErrorBoundaryState
> {
  state: SentryErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): SentryErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    if (!monitoringEnabled) {
      return;
    }

    void loadRuntime()
      .then((runtime) => runtime.captureReactException(error, errorInfo))
      .catch(() => {
        monitoringEnabled = false;
      });
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}
