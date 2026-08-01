const CHAT_SESSION_MESSAGE_WINDOW_MS = 24 * 60 * 60 * 1000;
const CHAT_SESSION_MESSAGE_STORAGE_KEY = 'residenciafiscal.chat-session-message-limit.v1';

export const CHAT_SESSION_MESSAGE_LIMIT_DEFAULT = 10;

interface StoredUsage {
  windowStartedAt: number;
  count: number;
}

export interface ChatSessionMessageUsage {
  allowed: boolean;
  count: number;
  limit: number;
  resetAt: number;
}

const storageForBrowser = (): Storage | null => {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
};

const validLimit = (value: number): number =>
  Number.isSafeInteger(value) && value > 0 ? value : CHAT_SESSION_MESSAGE_LIMIT_DEFAULT;

export const getChatSessionMessageLimit = (
  raw: string | undefined = import.meta.env?.VITE_CHAT_SESSION_MESSAGE_LIMIT
): number => {
  const parsed = Number(raw?.trim());
  return validLimit(parsed);
};

const readUsage = (storage: Storage | null, now: number): StoredUsage => {
  if (!storage) return { windowStartedAt: now, count: 0 };

  try {
    const raw = storage.getItem(CHAT_SESSION_MESSAGE_STORAGE_KEY);
    if (!raw) return { windowStartedAt: now, count: 0 };
    const parsed = JSON.parse(raw) as Partial<StoredUsage>;
    const windowStartedAt = parsed.windowStartedAt;
    const count = parsed.count;
    if (
      typeof windowStartedAt !== 'number' ||
      typeof count !== 'number' ||
      !Number.isSafeInteger(windowStartedAt) ||
      !Number.isSafeInteger(count) ||
      windowStartedAt > now ||
      count < 0
    ) {
      return { windowStartedAt: now, count: 0 };
    }
    if (now - windowStartedAt >= CHAT_SESSION_MESSAGE_WINDOW_MS) {
      return { windowStartedAt: now, count: 0 };
    }
    return { windowStartedAt, count };
  } catch {
    return { windowStartedAt: now, count: 0 };
  }
};

export const consumeChatSessionMessage = (
  storage: Storage | null = storageForBrowser(),
  now = Date.now(),
  configuredLimit = getChatSessionMessageLimit()
): ChatSessionMessageUsage => {
  const limit = validLimit(configuredLimit);
  const usage = readUsage(storage, now);
  const resetAt = usage.windowStartedAt + CHAT_SESSION_MESSAGE_WINDOW_MS;
  if (usage.count >= limit) {
    return { allowed: false, count: usage.count, limit, resetAt };
  }

  const next = { windowStartedAt: usage.windowStartedAt, count: usage.count + 1 };
  try {
    storage?.setItem(CHAT_SESSION_MESSAGE_STORAGE_KEY, JSON.stringify(next));
  } catch {
    // El límite es deliberadamente blando; si el navegador no permite persistir
    // localStorage, no bloqueamos el chat por un fallo de almacenamiento local.
  }
  return { allowed: true, count: next.count, limit, resetAt };
};
