import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  TYPING_STATUS_MESSAGES,
  TYPING_STATUS_ROTATION_MS,
  TypingIndicator,
} from '@/components/chat/TypingIndicator';

describe('TypingIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('expone un nombre accesible estable aunque el texto visible rote', () => {
    render(<TypingIndicator />);
    expect(screen.getByRole('status', { name: /preparando la respuesta/i })).toBeInTheDocument();
  });

  it('avanza por los textos de estado cada 5 segundos y se queda en el último', () => {
    render(<TypingIndicator />);
    const indicator = screen.getByRole('status');

    expect(TYPING_STATUS_MESSAGES.length).toBeGreaterThanOrEqual(3);
    expect(indicator).toHaveTextContent(TYPING_STATUS_MESSAGES[0]);

    for (const message of TYPING_STATUS_MESSAGES.slice(1)) {
      act(() => {
        vi.advanceTimersByTime(TYPING_STATUS_ROTATION_MS);
      });
      expect(indicator).toHaveTextContent(message);
    }

    // El último texto se mantiene: el ciclo no vuelve a empezar.
    act(() => {
      vi.advanceTimersByTime(TYPING_STATUS_ROTATION_MS * 3);
    });
    expect(indicator).toHaveTextContent(TYPING_STATUS_MESSAGES.at(-1) as string);
  });

  it('el primer texto habla de comprobar sentencias', () => {
    expect(TYPING_STATUS_MESSAGES[0]).toMatch(/comprobando sentencias/i);
    expect(TYPING_STATUS_ROTATION_MS).toBe(5000);
  });
});
