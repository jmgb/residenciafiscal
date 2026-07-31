/// <reference types="vite/client" />

declare const __SENTRY_RELEASE__: string;
/** Revisión del despliegue; se compara con la de `/version.json`. */
declare const __APP_RELEASE__: string;

interface ImportMetaEnv {
  readonly VITE_CHAT_MODE?: string;
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_SENTRY_ENABLED?: string;
  readonly VITE_SENTRY_ENVIRONMENT?: string;
  readonly VITE_SENTRY_TRACES_SAMPLE_RATE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
