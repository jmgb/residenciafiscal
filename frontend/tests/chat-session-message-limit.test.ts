import { describe, expect, it } from 'vitest';
import {
  CHAT_SESSION_MESSAGE_LIMIT_DEFAULT,
  consumeChatSessionMessage,
  getChatSessionMessageLimit,
} from '@/lib/chat-session-message-limit';

class MemoryStorage implements Storage {
  private readonly values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

describe('límite blando de mensajes por sesión', () => {
  it('usa diez mensajes por defecto y permite configurar un límite positivo', () => {
    expect(getChatSessionMessageLimit(undefined)).toBe(CHAT_SESSION_MESSAGE_LIMIT_DEFAULT);
    expect(getChatSessionMessageLimit('25')).toBe(25);
    expect(getChatSessionMessageLimit('0')).toBe(CHAT_SESSION_MESSAGE_LIMIT_DEFAULT);
    expect(getChatSessionMessageLimit('no-es-un-numero')).toBe(CHAT_SESSION_MESSAGE_LIMIT_DEFAULT);
  });

  it('permite diez mensajes y bloquea el undécimo durante 24 horas', () => {
    const storage = new MemoryStorage();
    const startedAt = Date.parse('2026-08-01T10:00:00.000Z');

    for (let count = 1; count <= 10; count += 1) {
      expect(consumeChatSessionMessage(storage, startedAt, 10)).toMatchObject({
        allowed: true,
        count,
        limit: 10,
      });
    }

    expect(consumeChatSessionMessage(storage, startedAt + 1, 10)).toMatchObject({
      allowed: false,
      count: 10,
      limit: 10,
    });
  });

  it('reinicia la ventana al cumplir 24 horas', () => {
    const storage = new MemoryStorage();
    const startedAt = Date.parse('2026-08-01T10:00:00.000Z');

    expect(consumeChatSessionMessage(storage, startedAt, 10).count).toBe(1);
    expect(consumeChatSessionMessage(storage, startedAt + 24 * 60 * 60 * 1000, 10)).toMatchObject({
      allowed: true,
      count: 1,
      limit: 10,
    });
  });
});
