import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatView } from '@/components/chat/ChatView';
import { useConversations } from '@/stores/useConversations';
import type { ChatChunk, ChatEngine, CorpusEntry } from '@/types/chat';

const source: CorpusEntry = {
  archivo: 'STS_107_2018.pdf',
  roj: 'STS 107/2018',
  ecli: 'ECLI:ES:TS:2018:107',
  organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
  fecha: '2018-01-16',
  resultado: 'GANA_AEAT',
  criterioDecisivo: ['CRIT_183_DIAS'],
  esCasoResidencia: true,
};

/** Motor de prueba: emite dos tokens, una fuente y termina. */
function createFakeEngine(): ChatEngine {
  return {
    async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
      if (signal.aborted) return;
      yield { type: 'token', text: 'Respuesta ' };
      yield { type: 'token', text: 'simulada.' };
      yield { type: 'sources', sources: [{ ...source, extracto: 'Extracto de prueba.' }] };
      yield { type: 'done' };
    },
  };
}

function renderChat(engine: ChatEngine = createFakeEngine()) {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path='/' element={<ChatView engine={engine} isStub />} />
        <Route path='/c/:conversationId' element={<ChatView engine={engine} isStub />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ChatView', () => {
  beforeEach(() => {
    window.localStorage.clear();
    useConversations.setState({ conversations: [] });
  });

  it('muestra la bienvenida y los prompts sugeridos cuando no hay mensajes', () => {
    renderChat();
    expect(screen.getByTestId('chat-welcome')).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
      })
    ).toBeInTheDocument();
  });

  it('muestra el aviso de motor simulado', () => {
    renderChat();
    expect(screen.getByRole('status', { name: /motor simulado/i })).toBeInTheDocument();
  });

  it('envía la consulta y pinta el mensaje del usuario', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), '¿Y los 183 días?');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('¿Y los 183 días?')).toBeInTheDocument();
  });

  it('pinta la respuesta del asistente al terminar el streaming', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText(/Respuesta simulada\./)).toBeInTheDocument();
  });

  it('renderiza las fuentes citadas', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('STS 107/2018')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Sentencias citadas' })).toBeInTheDocument();
  });

  it('despliega el extracto de una fuente al pulsarla', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await user.click(await screen.findByRole('button', { name: /STS 107\/2018/ }));

    expect(screen.getByText('Extracto de prueba.')).toBeInTheDocument();
  });

  it('un prompt sugerido lanza la consulta', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(
      screen.getByRole('button', {
        name: '¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?',
      })
    );

    expect(
      await screen.findByText('¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?')
    ).toBeInTheDocument();
  });

  it('guarda la conversación en el store', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta guardada');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    await waitFor(() => {
      expect(useConversations.getState().conversations).toHaveLength(1);
    });
    expect(useConversations.getState().conversations[0].title).toBe('consulta guardada');
  });

  it('muestra el botón de detener mientras se recibe la respuesta', async () => {
    const user = userEvent.setup();
    const slowEngine: ChatEngine = {
      async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
        if (signal.aborted) return;
        yield { type: 'token', text: 'primero ' };
        await new Promise((resolve) => setTimeout(resolve, 300));
        if (signal.aborted) return;
        yield { type: 'token', text: 'segundo' };
        yield { type: 'done' };
      },
    };
    renderChat(slowEngine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByRole('button', { name: 'Detener respuesta' })).toBeInTheDocument();
  });

  it('detener aborta el streaming y devuelve el botón de enviar', async () => {
    const user = userEvent.setup();
    const slowEngine: ChatEngine = {
      async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
        for (const text of ['uno ', 'dos ', 'tres ']) {
          if (signal.aborted) return;
          await new Promise((resolve) => setTimeout(resolve, 200));
          if (signal.aborted) return;
          yield { type: 'token', text };
        }
        yield { type: 'done' };
      },
    };
    renderChat(slowEngine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await user.click(await screen.findByRole('button', { name: 'Detener respuesta' }));

    expect(await screen.findByRole('button', { name: 'Enviar consulta' })).toBeInTheDocument();
  });

  it('rehidrata los mensajes de una conversación existente', () => {
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'consulta anterior',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    render(
      <MemoryRouter initialEntries={[`/c/${id}`]}>
        <Routes>
          <Route
            path='/c/:conversationId'
            element={<ChatView engine={createFakeEngine()} isStub />}
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('consulta anterior')).toBeInTheDocument();
    expect(screen.queryByTestId('chat-welcome')).not.toBeInTheDocument();
  });

  it('no envía consultas vacías', async () => {
    const engine = createFakeEngine();
    const spy = vi.spyOn(engine, 'askQuestion');
    const user = userEvent.setup();
    renderChat(engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), '   ');

    expect(screen.getByRole('button', { name: 'Enviar consulta' })).toBeDisabled();
    expect(spy).not.toHaveBeenCalled();
  });
});
