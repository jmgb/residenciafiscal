import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ChatDateDivider, formatConversationStart } from '@/components/chat/ChatDateDivider';

const AHORA = new Date('2026-08-06T12:00:00');

describe('formatConversationStart', () => {
  it('rotula el mismo día como hoy', () => {
    expect(formatConversationStart('2026-08-06T01:56:00', AHORA)).toBe('hoy 1:56');
  });

  it('rotula el día anterior como ayer', () => {
    expect(formatConversationStart('2026-08-05T23:10:00', AHORA)).toBe('ayer 23:10');
  });

  it('usa el día de la semana dentro de los últimos siete días', () => {
    expect(formatConversationStart('2026-08-04T01:56:00', AHORA)).toBe('martes 1:56');
  });

  it('escribe la fecha completa cuando el día de la semana ya no identifica el momento', () => {
    expect(formatConversationStart('2026-05-12T09:05:00', AHORA)).toBe('12 may 2026, 9:05');
  });

  it('no inventa etiqueta con una fecha inválida', () => {
    expect(formatConversationStart('no-es-una-fecha', AHORA)).toBe('');
  });
});

describe('ChatDateDivider', () => {
  it('pinta la marca temporal centrada al comienzo del hilo', () => {
    render(<ChatDateDivider createdAt={new Date().toISOString()} />);

    const divider = screen.getByTestId('chat-date-divider');
    expect(divider).toHaveClass('text-center');
    expect(divider.textContent).toMatch(/^hoy \d{1,2}:\d{2}$/);
  });

  it('no renderiza nada si la fecha no es válida', () => {
    render(<ChatDateDivider createdAt='' />);

    expect(screen.queryByTestId('chat-date-divider')).toBeNull();
  });
});
