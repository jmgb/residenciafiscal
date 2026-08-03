export type ChatDiagnosticDependency =
  | 'supabase'
  | 'openai'
  | 'gemini'
  | 'configuration'
  | 'internal';

export interface ChatDiagnostic {
  dependency: ChatDiagnosticDependency;
  operation: string;
  kind: string;
  code?: string;
  status?: number;
  retryable?: boolean;
  missing?: string[];
}

interface ErrorLike {
  code?: unknown;
  message?: unknown;
  status?: unknown;
}

const TOKEN = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/;
const DEPENDENCIES = new Set<ChatDiagnosticDependency>([
  'supabase',
  'openai',
  'gemini',
  'configuration',
  'internal',
]);

const token = (value: unknown): string | undefined => {
  if (typeof value !== 'string') return undefined;
  const normalized = value.trim();
  return TOKEN.test(normalized) ? normalized : undefined;
};

const status = (value: unknown): number | undefined => {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isInteger(numeric) && numeric >= 100 && numeric <= 599 ? numeric : undefined;
};

export const sanitizeChatDiagnostic = (value: ChatDiagnostic): ChatDiagnostic => {
  const dependency = DEPENDENCIES.has(value.dependency) ? value.dependency : 'internal';
  const code = token(value.code);
  const providerStatus = status(value.status);
  const missing = Array.isArray(value.missing)
    ? value.missing
        .map(token)
        .filter((item): item is string => Boolean(item))
        .slice(0, 20)
    : [];
  return {
    dependency,
    operation: token(value.operation) ?? 'unknown',
    kind: token(value.kind) ?? 'unknown',
    ...(code ? { code } : {}),
    ...(providerStatus !== undefined ? { status: providerStatus } : {}),
    ...(typeof value.retryable === 'boolean' ? { retryable: value.retryable } : {}),
    ...(missing.length ? { missing } : {}),
  };
};

const textOf = (error: unknown): string => {
  if (!error || typeof error !== 'object') return '';
  const message = (error as ErrorLike).message;
  return typeof message === 'string' ? message.toLowerCase() : '';
};

const codeOf = (error: unknown): string | undefined => {
  if (!error || typeof error !== 'object') return undefined;
  return token((error as ErrorLike).code);
};

const statusOf = (error: unknown): number | undefined => {
  if (!error || typeof error !== 'object') return undefined;
  return status((error as ErrorLike).status);
};

const supabaseKind = (error: unknown): string => {
  const code = codeOf(error);
  const message = textOf(error);
  if (
    code === 'PGRST202' ||
    /function .* does not exist|could not find the function/.test(message)
  ) {
    return 'rpc_not_found';
  }
  if (code === '42501' || /permission|not authorized|forbidden/.test(message)) {
    return 'permission_denied';
  }
  if (
    code?.startsWith('22') ||
    /invalid .*request|invalid .*completion|invalid input/.test(message)
  ) {
    return 'invalid_payload';
  }
  if (code?.startsWith('23') || /constraint|duplicate key/.test(message)) {
    return 'constraint_violation';
  }
  if (/not found/.test(message)) return 'request_not_found';
  if (/timeout|timed out|connection|network|fetch failed|unavailable/.test(message)) {
    return 'unavailable';
  }
  return 'rpc_error';
};

export const supabaseDiagnostic = (operation: string, error: unknown): ChatDiagnostic => {
  const kind = supabaseKind(error);
  return sanitizeChatDiagnostic({
    dependency: 'supabase',
    operation,
    kind,
    code: codeOf(error),
    status: statusOf(error),
    retryable: ['unavailable', 'rpc_error'].includes(kind),
  });
};

export const providerDiagnostic = (
  dependency: Extract<ChatDiagnosticDependency, 'openai' | 'gemini'>,
  operation: string,
  error: unknown
): ChatDiagnostic => {
  const providerStatus = statusOf(error);
  const message = textOf(error);
  const timedOut =
    providerStatus === 408 || providerStatus === 504 || /timeout|timed out|aborted/.test(message);
  const retryable =
    timedOut || providerStatus === 429 || (providerStatus !== undefined && providerStatus >= 500);
  return sanitizeChatDiagnostic({
    dependency,
    operation,
    kind: timedOut ? 'provider_timeout' : 'provider_error',
    code: codeOf(error),
    status: providerStatus,
    retryable,
  });
};

export class ChatDiagnosticError extends Error {
  readonly diagnostic: ChatDiagnostic;

  constructor(message: string, diagnostic: ChatDiagnostic) {
    super(message);
    this.name = 'ChatDiagnosticError';
    this.diagnostic = sanitizeChatDiagnostic(diagnostic);
  }
}

export const diagnosticFromError = (error: unknown): ChatDiagnostic | null => {
  if (!error || typeof error !== 'object') return null;
  const diagnostic = (error as { diagnostic?: unknown }).diagnostic;
  if (!diagnostic || typeof diagnostic !== 'object') return null;
  const candidate = diagnostic as ChatDiagnostic;
  if (typeof candidate.dependency !== 'string' || typeof candidate.operation !== 'string') {
    return null;
  }
  return sanitizeChatDiagnostic(candidate);
};
