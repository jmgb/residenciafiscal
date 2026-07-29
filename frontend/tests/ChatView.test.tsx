import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes, useLocation } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatView } from '@/components/chat/ChatView';
import { COUNTRY_ROUTES } from '@/data/countryRoutes';
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

/**
 * Motor con una pausa CONTROLADA a mitad de respuesta: deja detener el test justo
 * mientras se está recibiendo la respuesta, sin depender de temporizadores.
 */
function createGatedEngine() {
  let release = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const state = { signal: undefined as AbortSignal | undefined, reachedSecondHalf: false };

  const engine: ChatEngine = {
    async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
      state.signal = signal;
      if (signal.aborted) return;
      yield { type: 'token', text: 'primer tramo. ' };
      await gate;
      if (signal.aborted) return;
      state.reachedSecondHalf = true;
      yield { type: 'token', text: 'segundo tramo.' };
      yield { type: 'done' };
    },
  };

  return { engine, state, release: () => release() };
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid='location'>{`${location.pathname}${location.hash}`}</div>;
}

function renderChatAt(
  initialEntries: string[],
  engine: ChatEngine = createFakeEngine(),
  navTargets: string[] = []
) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <LocationProbe />
      {navTargets.map((to) => (
        <Link key={to} to={to}>{`ir a ${to}`}</Link>
      ))}
      <Routes>
        <Route path='/' element={<ChatView engine={engine} isStub />} />
        <Route path='/c/:conversationId' element={<ChatView engine={engine} isStub />} />
      </Routes>
    </MemoryRouter>
  );
}

function renderChat(engine: ChatEngine = createFakeEngine()) {
  return renderChatAt(['/'], engine);
}

/**
 * jsdom no calcula layout: `scrollHeight` y `clientHeight` valen 0 y el contenedor nunca
 * parece desplazable. Se falsean para poder comprobar la lógica de autoscroll.
 * `scrollTop` sí es una propiedad real y escribible en jsdom, así que se lee tal cual.
 */
function fakeLayout(element: HTMLElement, clientHeight: number, scrollHeight: () => number) {
  Object.defineProperty(element, 'clientHeight', { configurable: true, get: () => clientHeight });
  Object.defineProperty(element, 'scrollHeight', { configurable: true, get: scrollHeight });
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

  it('pasa el país seleccionado al motor de consulta', async () => {
    const user = userEvent.setup();
    const askQuestion = vi.fn(async function* () {
      yield { type: 'done' as const };
    });
    const engine: ChatEngine = { askQuestion };

    render(
      <MemoryRouter initialEntries={['/mexico']}>
        <ChatView
          engine={engine}
          isStub
          country={COUNTRY_ROUTES.find((route) => route.path === '/mexico')}
        />
      </MemoryRouter>
    );

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(askQuestion).toHaveBeenCalledWith(expect.any(Array), expect.any(AbortSignal), {
      countryPath: '/mexico',
      countryName: 'México',
    });
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

  it('detener antes del primer token no deja una burbuja vacía', async () => {
    const user = userEvent.setup();
    const engine: ChatEngine = {
      async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
        await new Promise<void>((resolve) => {
          signal.addEventListener('abort', () => resolve(), { once: true });
        });
      },
    };
    renderChat(engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await user.click(await screen.findByRole('button', { name: 'Detener respuesta' }));

    expect(await screen.findByText('Respuesta detenida.')).toBeInTheDocument();
  });

  it('marca una respuesta parcial si el motor falla durante el streaming', async () => {
    const user = userEvent.setup();
    const engine: ChatEngine = {
      async *askQuestion(): AsyncIterable<ChatChunk> {
        yield { type: 'token', text: 'Respuesta parcial.' };
        throw new Error('fallo de red');
      },
    };
    renderChat(engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText(/No se ha podido completar la consulta/)).toBeInTheDocument();
    expect(screen.getByText(/Respuesta parcial/)).toBeInTheDocument();
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

  it('cambiar de conversación durante el streaming lo aborta y libera el composer', async () => {
    const user = userEvent.setup();
    const otherId = useConversations.getState().createConversation();
    const { engine, state, release } = createGatedEngine();
    renderChatAt(['/'], engine, [`/c/${otherId}`]);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta larga');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    expect(await screen.findByText(/primer tramo\./)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Detener respuesta' })).toBeInTheDocument();

    const streamingId = useConversations
      .getState()
      .conversations.find((conversation) => conversation.id !== otherId)?.id;
    expect(streamingId).toBeDefined();

    await user.click(screen.getByRole('link', { name: `ir a /c/${otherId}` }));

    expect(screen.getByTestId('location')).toHaveTextContent(`/c/${otherId}`);
    expect(state.signal?.aborted).toBe(true);
    // El composer de la conversación nueva no queda bloqueado en "Detener respuesta".
    expect(screen.getByRole('button', { name: 'Enviar consulta' })).toBeInTheDocument();

    release();
    await waitFor(() => {
      const messages = useConversations.getState().getConversation(streamingId as string)?.messages;
      expect(messages?.at(-1)?.isStreaming).toBe(false);
    });
    // La respuesta abortada conserva lo que llegó y no sigue creciendo.
    const aborted = useConversations.getState().getConversation(streamingId as string);
    expect(state.reachedSecondHalf).toBe(false);
    expect(aborted?.messages.at(-1)?.content).toBe('primer tramo. ');
  });

  it('el primer envío desde / no se autoaborta al navegar a /c/:id', async () => {
    const user = userEvent.setup();
    // El motor comprueba `signal.aborted` DESPUÉS de la pausa: si la navegación a
    // `/c/:id` abortara su propio stream, la respuesta quedaría a medias.
    const engine: ChatEngine = {
      async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
        yield { type: 'token', text: 'primera parte. ' };
        await new Promise((resolve) => setTimeout(resolve, 20));
        if (signal.aborted) return;
        yield { type: 'token', text: 'segunda parte.' };
        yield { type: 'done' };
      },
    };
    renderChatAt(['/'], engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('primera parte. segunda parte.')).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/c\/.+/);
    expect(await screen.findByRole('button', { name: 'Enviar consulta' })).toBeInTheDocument();
  });

  it('una URL con una conversación inexistente redirige a /', async () => {
    renderChatAt(['/c/no-existe']);

    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent('/');
    });
    expect(screen.getByTestId('location')).not.toHaveTextContent('no-existe');
    expect(screen.getByTestId('chat-welcome')).toBeInTheDocument();
  });

  it('desde una URL con conversación inexistente la consulta no se pierde', async () => {
    const user = userEvent.setup();
    renderChatAt(['/c/no-existe']);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta huérfana');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('consulta huérfana')).toBeInTheDocument();
    expect(await screen.findByText(/Respuesta simulada\./)).toBeInTheDocument();
    await waitFor(() => {
      expect(useConversations.getState().conversations).toHaveLength(1);
    });
    expect(useConversations.getState().conversations[0].id).not.toBe('no-existe');
  });

  it('el autoscroll sigue al texto que llega mientras se recibe la respuesta', async () => {
    const user = userEvent.setup();
    const { engine, release } = createGatedEngine();
    renderChatAt(['/'], engine);

    const container = screen.getByTestId('chat-scroll');
    let scrollHeight = 400;
    fakeLayout(container, 300, () => scrollHeight);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await screen.findByText(/primer tramo\./);

    // El texto en streaming crece sin que cambie el número de mensajes.
    scrollHeight = 1200;
    release();
    await screen.findByText(/segundo tramo\./);

    await waitFor(() => {
      expect(container.scrollTop).toBe(1200);
    });
  });

  it('no arrastra al usuario abajo si ha subido a leer durante el streaming', async () => {
    const user = userEvent.setup();
    const { engine, release } = createGatedEngine();
    renderChatAt(['/'], engine);

    const container = screen.getByTestId('chat-scroll');
    let scrollHeight = 400;
    fakeLayout(container, 300, () => scrollHeight);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await screen.findByText(/primer tramo\./);

    // El usuario sube a leer: queda a 100px del fondo, fuera del margen de tolerancia.
    container.scrollTop = 0;
    fireEvent.scroll(container);

    scrollHeight = 1200;
    release();
    await screen.findByText(/segundo tramo\./);

    expect(container.scrollTop).toBe(0);
  });
});
