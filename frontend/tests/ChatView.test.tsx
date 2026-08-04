import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes, useLocation } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatView } from '@/components/chat/ChatView';
import { comparisonIdForLatestQuestion } from '@/components/chat/useDeepResearch';
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

function fakeMessageGeometry(
  container: HTMLElement,
  assistantContentTop: number,
  containerTop = 20
) {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (
    this: HTMLElement
  ) {
    const top =
      this === container
        ? containerTop
        : this.dataset.chatMessageId && this.querySelector('[data-testid="chat-bubble-assistant"]')
          ? containerTop + assistantContentTop - container.scrollTop
          : 0;
    return {
      x: 0,
      y: top,
      top,
      right: 0,
      bottom: top,
      left: 0,
      width: 0,
      height: 0,
      toJSON: () => ({}),
    };
  });
}

/** Deja en el head una única meta robots `noindex`, como la de la shell. */
function seedShellRobotsMeta() {
  document.head.querySelector('meta[name="robots"]')?.remove();
  const robots = document.createElement('meta');
  robots.setAttribute('name', 'robots');
  robots.setAttribute('content', 'noindex, follow');
  document.head.appendChild(robots);
}

describe('ChatView', () => {
  it('no vincula C con una comparación anterior de otra pregunta', () => {
    expect(
      comparisonIdForLatestQuestion([
        {
          id: 'u1',
          role: 'user',
          content: 'primera pregunta',
          createdAt: '2026-08-03T10:00:00Z',
        },
        {
          id: 'a1',
          role: 'assistant',
          content: '',
          comparisonId: 'chat-comparison-1',
          createdAt: '2026-08-03T10:00:01Z',
        },
        {
          id: 'u2',
          role: 'user',
          content: 'segunda pregunta',
          createdAt: '2026-08-03T10:01:00Z',
        },
        {
          id: 'a2',
          role: 'assistant',
          content: 'respuesta no comparativa',
          createdAt: '2026-08-03T10:01:01Z',
        },
      ])
    ).toBeUndefined();
  });

  beforeEach(() => {
    window.localStorage.clear();
    useConversations.setState({ conversations: [] });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('solo la ruta canónica queda indexable en runtime', async () => {
    seedShellRobotsMeta();

    render(
      <MemoryRouter initialEntries={['/espana']}>
        <Routes>
          <Route
            path='/espana'
            element={<ChatView engine={createFakeEngine()} isStub canonicalPath='/espana' />}
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
        'content',
        'index, follow'
      );
    });
  });

  it('las rutas solo-SPA no deshacen el noindex de la shell al renderizarse', async () => {
    // Un crawler que ejecute JavaScript en `/consulta` o `/c/:id` ve el DOM
    // final: si el hook las marcara `index`, revertiría la política de la shell.
    for (const path of ['/consulta', '/c/abc123']) {
      seedShellRobotsMeta();

      const view = render(
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route
              path='/consulta'
              element={<ChatView engine={createFakeEngine()} isStub canonicalPath='/espana' />}
            />
            <Route
              path='/c/:conversationId'
              element={<ChatView engine={createFakeEngine()} isStub canonicalPath='/espana' />}
            />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(document.title).toBe('Residencia fiscal en España: jurisprudencia del art. 9 LIRPF');
      });
      expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
        'content',
        'noindex, follow'
      );
      view.unmount();
    }
  });

  it('muestra la bienvenida y los prompts sugeridos cuando no hay mensajes', () => {
    renderChat();
    expect(screen.getByTestId('chat-welcome')).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: '¿Qué pruebas valora el Tribunal Supremo para acreditar o discutir el cómputo de los 183 días?',
      })
    ).toBeInTheDocument();
  });

  // El aviso del stub vivía en la banda ámbar y ensuciaba la home; el aviso de
  // contenido simulado lo lleva ahora el propio texto de cada respuesta del stub.
  it('no pinta ninguna banda de aviso cuando el motor es simulado', () => {
    renderChat();

    expect(screen.queryByRole('status', { name: /motor simulado/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('status', { name: /investigación jurídica/i })
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/está activo el motor simulado/i)).not.toBeInTheDocument();
  });

  it('mantiene el aviso jurídico y el enlace de privacidad cuando el motor es real', () => {
    render(
      <MemoryRouter>
        <ChatView engine={createFakeEngine()} isStub={false} />
      </MemoryRouter>
    );

    const banner = screen.getByRole('status', { name: /investigación jurídica/i });
    expect(banner).toHaveTextContent(/^Aviso:/i);
    expect(banner).not.toHaveTextContent(/respuestas.*simuladas/i);
    expect(banner).toHaveTextContent(/no constituye asesoramiento legal ni jurídico/i);
    expect(within(banner).getByRole('link', { name: 'Privacidad' })).toHaveAttribute(
      'href',
      '/privacidad'
    );
  });

  it('envía la consulta y pinta el mensaje del usuario', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), '¿Y los 183 días?');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('¿Y los 183 días?')).toBeInTheDocument();
  });

  it('ofrece investigación profunda fuera de A/B y encola el job al pulsar el botón', async () => {
    vi.stubEnv('VITE_DEEP_RESEARCH_ENABLED', 'true');
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      if (String(input) === '/api/deep-research') {
        return Response.json({ job_id: 'deep-ui-1', status: 'queued' }, { status: 202 });
      }
      return Response.json({
        job_id: 'deep-ui-1',
        status: 'queued',
        stage: 'searching',
        result: null,
        error: null,
      });
    });
    vi.stubGlobal('fetch', fetchMock);
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta para C');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    const deepResearchButton = await screen.findByRole('button', {
      name: 'Iniciar investigación profunda',
    });
    expect(deepResearchButton).toBeInTheDocument();

    await user.click(deepResearchButton);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/deep-research',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('consulta para C'),
        })
      );
    });
    const startCall = fetchMock.mock.calls.find(
      ([input]) => String(input) === '/api/deep-research'
    );
    expect(JSON.parse(String(startCall?.[1]?.body))).toMatchObject({
      comparison_id: null,
    });
    expect(screen.getByText('Investigación profunda en cola')).toBeInTheDocument();
  });

  it('bloquea el chat al alcanzar el límite configurable de la sesión', async () => {
    vi.stubEnv('VITE_CHAT_SESSION_MESSAGE_LIMIT', '1');
    const user = userEvent.setup();
    const askQuestion = vi.fn(async function* () {
      yield { type: 'done' as const };
    });
    renderChat({ askQuestion });

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'primera consulta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('primera consulta')).toBeInTheDocument();
    expect(askQuestion).toHaveBeenCalledOnce();
    expect(screen.getByRole('status', { name: /límite de mensajes de sesión/i })).toHaveTextContent(
      /1 mensaje/i
    );
    expect(screen.getByRole('textbox', { name: 'Consulta' })).toBeDisabled();
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

    // La comparación sigue siendo exacta y no `objectContaining`: un campo nuevo
    // en el contexto viaja al backend y debe declararse aquí a propósito. El
    // `conversationId` lo genera el envío, así que solo se comprueba su tipo.
    expect(askQuestion).toHaveBeenCalledWith(expect.any(Array), expect.any(AbortSignal), {
      countryPath: '/mexico',
      countryName: 'México',
      conversationId: expect.any(String),
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

  it('presenta la comparación A/B como dos respuestas independientes con su coste', async () => {
    const user = userEvent.setup();
    const cost = {
      currency: 'USD' as const,
      amountUsd: '0.012345',
      costMicrousd: 12345,
      measurement: 'ACTUAL' as const,
      scope: 'REQUEST_MARGINAL' as const,
      pricingVersion: '2026-07-31',
      inputTokens: 100,
      outputTokens: 20,
      retrievedDocumentTokens: 0,
      excludesCorpusPreparation: true as const,
    };
    const engine: ChatEngine = {
      async *askQuestion(): AsyncIterable<ChatChunk> {
        yield { type: 'answer_start', strategy: 'current_structured' };
        yield { type: 'token', strategy: 'current_structured', text: 'Respuesta estructurada.' };
        yield {
          type: 'strategy_sources',
          strategy: 'current_structured',
          sources: [
            {
              strategy: 'current_structured',
              judgmentId: 'STS-107-2018',
              page: 7,
              sourceSha256: 'a'.repeat(64),
              quote: 'Cita literal A.',
              verification: 'EXACT',
            },
          ],
        };
        yield {
          type: 'answer_done',
          strategy: 'current_structured',
          status: 'completa',
          limits: [],
          cost,
          model: 'luna',
          latencyMs: 100,
        };
        yield { type: 'answer_start', strategy: 'gemini_file_search' };
        yield { type: 'token', strategy: 'gemini_file_search', text: 'Respuesta File Search.' };
        yield { type: 'strategy_sources', strategy: 'gemini_file_search', sources: [] };
        yield {
          type: 'answer_done',
          strategy: 'gemini_file_search',
          status: 'parcial',
          limits: ['Cobertura limitada.'],
          cost: { ...cost, amountUsd: '0.020000', costMicrousd: 20000 },
          model: 'gemini-2.5-flash',
          latencyMs: 200,
        };
        yield { type: 'done', requestId: 'chat-comparison-1' };
      },
    };
    renderChat(engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta comparativa');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    const structured = await screen.findByRole('tabpanel', {
      name: 'Respuesta de la opción A',
    });
    const fileSearch = screen.getByRole('tabpanel', { name: 'Respuesta de la opción B' });
    expect(structured).toHaveTextContent('Respuesta estructurada.');
    expect(structured).toHaveTextContent('Coste: 0.012 USD');
    expect(structured).toHaveTextContent('Cita literal A.');
    expect(within(structured).queryByText(/SHA-256/)).not.toBeInTheDocument();
    expect(
      within(structured).getByRole('link', { name: 'Abrir sentencia STS 107/2018' })
    ).toHaveAttribute('href', '/sentencias/sts-107-2018.pdf');
    expect(
      within(structured).getByRole('link', { name: 'Descargar PDF STS 107/2018' })
    ).toHaveAttribute('download', 'STS_107_2018.pdf');
    expect(fileSearch).toHaveTextContent('Respuesta File Search.');
    expect(fileSearch).toHaveTextContent('Coste: 0.020 USD');
    expect(fileSearch).toHaveTextContent('Cobertura limitada.');
    expect(screen.getByText(/comparación experimental/i)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Valorar comparación' })).toBeInTheDocument();
    const assistant = useConversations
      .getState()
      .conversations[0]?.messages.find((message) => message.role === 'assistant');
    expect(assistant?.comparisonId).toBe('chat-comparison-1');
  });

  it('conserva A y muestra el fallo de B si se corta el stream comparativo', async () => {
    const user = userEvent.setup();
    const engine: ChatEngine = {
      async *askQuestion(): AsyncIterable<ChatChunk> {
        yield { type: 'answer_start', strategy: 'current_structured' };
        yield { type: 'token', strategy: 'current_structured', text: 'Respuesta A conservada.' };
        yield {
          type: 'answer_done',
          strategy: 'current_structured',
          status: 'completa',
          limits: [],
          cost: {
            currency: 'USD',
            amountUsd: '0.010000',
            costMicrousd: 10000,
            measurement: 'ACTUAL',
            scope: 'REQUEST_MARGINAL',
            pricingVersion: '2026-07-31',
            inputTokens: 100,
            outputTokens: 20,
            retrievedDocumentTokens: 0,
            excludesCorpusPreparation: true,
          },
          model: 'luna',
          latencyMs: 100,
        };
        throw new Error('corte antes de B');
      },
    };
    renderChat(engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(
      await screen.findByRole('tabpanel', { name: 'Respuesta de la opción A' })
    ).toHaveTextContent('Respuesta A conservada.');
    expect(screen.getByRole('tabpanel', { name: 'Respuesta de la opción B' })).toHaveTextContent(
      /no se ha podido completar esta estrategia/i
    );
  });

  it('despliega el extracto de una fuente al pulsarla', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await user.click(await screen.findByRole('button', { name: /STS 107\/2018/ }));

    expect(screen.getByText('Extracto de prueba.')).toBeInTheDocument();
  });

  it.each([
    [
      '¿Qué pruebas valora el Tribunal Supremo para acreditar o discutir el cómputo de los 183 días?',
      /no existe una lista cerrada/i,
      /STS 3498\/2025/,
    ],
    [
      '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?',
      /duración o intensidad/i,
      /STS 115\/2018/,
    ],
    [
      '¿Qué valor probatorio tiene un certificado de residencia fiscal extranjero?',
      /no puede ignorarse/i,
      /STS 3498\/2025/,
    ],
    [
      '¿Cuándo se aplica la regla de desempate del art. 4 del CDI aplicable?',
      /doble residencia/i,
      /STS 3498\/2025/,
    ],
  ])(
    'el prompt editorial %s responde sin llamar al comparador',
    async (question, answerExcerpt, sourceLabel) => {
      vi.useFakeTimers();
      const askQuestion = vi.fn(async function* () {
        yield { type: 'done' as const };
      });
      renderChat({ askQuestion });

      fireEvent.click(screen.getByRole('button', { name: question }));

      expect(screen.getByText(question)).toBeInTheDocument();
      await act(async () => vi.advanceTimersByTimeAsync(12_000));
      expect(screen.getByRole('region', { name: 'Respuesta editorial' })).toHaveTextContent(
        answerExcerpt
      );
      expect(screen.getByText(sourceLabel)).toBeInTheDocument();
      expect(screen.queryByText('Respuesta editorial')).not.toBeInTheDocument();
      expect(screen.queryByText(/Actualizada el/)).not.toBeInTheDocument();
      expect(screen.queryByText(/SHA-256/)).not.toBeInTheDocument();
      expect(screen.queryByText(/comparación experimental/i)).not.toBeInTheDocument();
      expect(askQuestion).not.toHaveBeenCalled();
    }
  );

  it('muestra la animación real durante 12 segundos antes de la respuesta editorial', async () => {
    vi.useFakeTimers();
    renderChat();
    const question = '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?';

    fireEvent.click(screen.getByRole('button', { name: question }));

    expect(screen.getByText(question)).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'Preparando la respuesta' })).toHaveTextContent(
      'Comprobando sentencias sobre el tema…'
    );
    expect(screen.queryByRole('region', { name: 'Respuesta editorial' })).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(4000));
    expect(screen.getByRole('status', { name: 'Preparando la respuesta' })).toHaveTextContent(
      'Analizando los criterios aplicados por los tribunales…'
    );

    act(() => vi.advanceTimersByTime(7999));
    expect(screen.getByRole('status', { name: 'Preparando la respuesta' })).toHaveTextContent(
      'Seleccionando extractos relevantes…'
    );
    expect(screen.queryByRole('region', { name: 'Respuesta editorial' })).not.toBeInTheDocument();

    await act(async () => vi.advanceTimersByTimeAsync(1));

    expect(screen.getByRole('region', { name: 'Respuesta editorial' })).toBeInTheDocument();
    expect(
      screen.queryByRole('status', { name: 'Preparando la respuesta' })
    ).not.toBeInTheDocument();
  });

  it('sitúa el inicio de una respuesta editorial en la parte superior de lectura', async () => {
    vi.useFakeTimers();
    renderChat();
    const container = screen.getByTestId('chat-scroll');
    fakeLayout(container, 300, () => 1200);
    fakeMessageGeometry(container, 260);

    fireEvent.click(
      screen.getByRole('button', {
        name: '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?',
      })
    );
    await act(async () => vi.advanceTimersByTimeAsync(12_000));

    expect(screen.getByRole('link', { name: 'Abrir sentencia STS 115/2018' })).toHaveAttribute(
      'href',
      '/sentencias/sts-115-2018.pdf'
    );
    expect(screen.getByRole('link', { name: 'Descargar PDF STS 115/2018' })).toHaveAttribute(
      'download',
      'STS_115_2018.pdf'
    );

    expect(container.scrollTop).toBe(260);
  });

  it('el mismo texto escrito manualmente sigue siendo una consulta al motor', async () => {
    const user = userEvent.setup();
    const askQuestion = vi.fn(async function* () {
      yield { type: 'done' as const };
    });
    renderChat({ askQuestion });
    const question = '¿Qué valor probatorio tiene un certificado de residencia fiscal extranjero?';

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), question);
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(askQuestion).toHaveBeenCalledOnce();
    expect(screen.queryByRole('region', { name: 'Respuesta editorial' })).not.toBeInTheDocument();
  });

  it('una respuesta editorial no consume el límite de consultas al motor', async () => {
    vi.stubEnv('VITE_CHAT_SESSION_MESSAGE_LIMIT', '1');
    vi.useFakeTimers();
    const askQuestion = vi.fn(async function* () {
      yield { type: 'done' as const };
    });
    renderChat({ askQuestion });

    fireEvent.click(
      screen.getByRole('button', {
        name: '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?',
      })
    );

    expect(screen.getByRole('textbox', { name: 'Consulta' })).toBeEnabled();
    expect(
      screen.queryByRole('status', { name: /límite de mensajes de sesión/i })
    ).not.toBeInTheDocument();
    expect(askQuestion).not.toHaveBeenCalled();

    await act(async () => vi.advanceTimersByTimeAsync(12_000));
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

  it('mientras se espera el primer token solo se ve el indicador, sin burbuja vacía', async () => {
    const user = userEvent.setup();
    let release = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const engine: ChatEngine = {
      async *askQuestion(): AsyncIterable<ChatChunk> {
        await gate;
        yield { type: 'token', text: 'Respuesta tras la espera.' };
        yield { type: 'done' };
      },
    };
    renderChat(engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(
      await screen.findByRole('status', { name: /preparando la respuesta/i })
    ).toBeInTheDocument();
    // La burbuja del asistente no aparece hasta que hay contenido que enseñar.
    expect(screen.queryByTestId('chat-bubble-assistant')).not.toBeInTheDocument();

    release();
    expect(await screen.findByText('Respuesta tras la espera.')).toBeInTheDocument();
    expect(screen.getByTestId('chat-bubble-assistant')).toBeInTheDocument();
    expect(
      screen.queryByRole('status', { name: /preparando la respuesta/i })
    ).not.toBeInTheDocument();
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

  it('sigue el streaming y al terminar sitúa el inicio de la respuesta arriba', async () => {
    const user = userEvent.setup();
    const { engine, release } = createGatedEngine();
    renderChatAt(['/'], engine);

    const container = screen.getByTestId('chat-scroll');
    let scrollHeight = 400;
    fakeLayout(container, 300, () => scrollHeight);
    fakeMessageGeometry(container, 240);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await screen.findByText(/primer tramo\./);
    await waitFor(() => {
      expect(container.scrollTop).toBe(400);
    });

    // El texto en streaming crece sin que cambie el número de mensajes.
    scrollHeight = 1200;
    release();
    await screen.findByText(/segundo tramo\./);

    await waitFor(() => {
      expect(container.scrollTop).toBe(240);
    });
  });

  it('no arrastra durante el streaming y al terminar abre la respuesta desde su inicio', async () => {
    const user = userEvent.setup();
    const { engine, release } = createGatedEngine();
    renderChatAt(['/'], engine);

    const container = screen.getByTestId('chat-scroll');
    let scrollHeight = 400;
    fakeLayout(container, 300, () => scrollHeight);
    fakeMessageGeometry(container, 240);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await screen.findByText(/primer tramo\./);

    // El usuario sube a leer: queda a 100px del fondo, fuera del margen de tolerancia.
    container.scrollTop = 0;
    fireEvent.scroll(container);

    scrollHeight = 1200;
    release();
    await screen.findByText(/segundo tramo\./);

    await waitFor(() => {
      expect(container.scrollTop).toBe(240);
    });
  });
});
