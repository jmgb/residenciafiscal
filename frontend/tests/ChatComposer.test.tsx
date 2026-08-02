import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ChatComposer } from '@/components/chat/ChatComposer';

describe('ChatComposer', () => {
  it('acorta el placeholder predeterminado en móvil', async () => {
    const matchMedia = vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
    vi.stubGlobal('matchMedia', matchMedia);

    render(<ChatComposer onSend={vi.fn()} onStop={vi.fn()} isStreaming={false} />);

    expect(await screen.findByPlaceholderText('Escribe tu consulta...')).toBeInTheDocument();
  });

  it('impide enviar más de 500 caracteres, igual que el backend', () => {
    const onSend = vi.fn();
    render(<ChatComposer onSend={onSend} onStop={vi.fn()} isStreaming={false} />);

    fireEvent.change(screen.getByLabelText('Consulta'), {
      target: { value: 'a'.repeat(501) },
    });

    expect(screen.getByRole('button', { name: 'Enviar consulta' })).toBeDisabled();
    expect(screen.getByText('501 / 500')).toBeInTheDocument();
  });
});
