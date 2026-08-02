import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { chatEngine } from '@/lib/chat-engine';
import { useConversations } from '@/stores/useConversations';

function LocationProbe() {
  const location = useLocation();
  return <div data-testid='location'>{location.pathname}</div>;
}

describe('navegación del chat de España', () => {
  beforeEach(() => {
    window.localStorage.clear();
    useConversations.setState({ conversations: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('conserva la primera respuesta al pasar de /espana a la conversación', async () => {
    const user = userEvent.setup();
    let releaseResponse = () => {};
    const responseGate = new Promise<void>((resolve) => {
      releaseResponse = resolve;
    });
    let requestSignal: AbortSignal | undefined;

    vi.spyOn(chatEngine, 'askQuestion').mockImplementation(async function* (_messages, signal) {
      requestSignal = signal;
      await responseGate;
      if (signal.aborted) return;
      yield { type: 'token', text: 'Respuesta conservada.' };
      yield { type: 'done' };
    });

    render(
      <MemoryRouter initialEntries={['/espana']}>
        <LocationProbe />
        <App />
      </MemoryRouter>
    );

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'primera consulta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent(/^\/c\//);
    });
    expect(requestSignal?.aborted).toBe(false);

    releaseResponse();

    expect(await screen.findByText('Respuesta conservada.')).toBeInTheDocument();
  });
});
