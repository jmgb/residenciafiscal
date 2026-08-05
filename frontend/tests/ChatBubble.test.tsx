import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ChatBubble } from '@/components/chat/ChatBubble';

describe('ChatBubble', () => {
  it('usa tokens de marca para la burbuja oscura del usuario', () => {
    render(
      <ChatBubble
        message={{
          id: 'user-1',
          role: 'user',
          content: 'como estas',
          createdAt: '2026-08-05T10:00:00Z',
        }}
      />
    );

    const bubble = screen.getByTestId('chat-bubble-user');
    expect(bubble).toHaveClass('bg-foreground');
    expect(bubble).not.toHaveClass('bg-black');
    expect(screen.getByText('como estas')).toHaveClass('text-background');
    expect(screen.getByText('como estas')).not.toHaveClass('text-white');
  });
});
