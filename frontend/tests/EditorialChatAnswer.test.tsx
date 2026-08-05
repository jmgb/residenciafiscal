import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EditorialChatAnswer } from '@/components/chat/EditorialChatAnswer';
import type { ChatMessage } from '@/types/chat';

describe('EditorialChatAnswer', () => {
  it('ofrece acciones de copia y fuentes para una respuesta editorial', () => {
    const message: ChatMessage = {
      id: 'editorial-1',
      role: 'assistant',
      content: 'Respuesta editorial verificada.',
      createdAt: '2026-08-05T10:00:00Z',
      editorial: {
        answerId: 'answer-1',
        version: '1',
        updatedAt: '2026-08-05',
        sources: [
          {
            judgmentId: 'STS-107-2018',
            roj: 'STS 107/2018',
            ecli: 'ECLI:ES:TS:2018:107',
            page: 7,
            sourceSha256: 'a'.repeat(64),
            quote: 'Cita literal editorial.',
            verification: 'EXACT',
          },
        ],
      },
    };

    render(<EditorialChatAnswer message={message} />);

    expect(screen.getByRole('button', { name: 'Copiar respuesta' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Descargar fuentes' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver fuentes' })).toHaveAttribute(
      'href',
      '#chat-editorial-sources-editorial-1'
    );
  });
});
