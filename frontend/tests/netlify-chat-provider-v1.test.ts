import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { createResponse } = vi.hoisted(() => ({
  createResponse: vi.fn(),
}));

vi.mock('openai', () => ({
  default: class OpenAI {
    responses = { create: createResponse };
  },
}));

import { ChatDiagnosticError } from '../netlify/functions/chat/chat-diagnostics';
import {
  createGeminiInteraction,
  createOpenAIWriter,
} from '../netlify/functions/chat/provider-adapters';

describe('adaptador OpenAI de la Function', () => {
  it('da a Luna high margen de 4.000 tokens para completar el JSON', async () => {
    createResponse.mockResolvedValueOnce({
      output_text: JSON.stringify({
        status: 'pregunta',
        claims: [],
        limits: [],
      }),
      usage: { input_tokens: 10, output_tokens: 5 },
      model: 'gpt-6-luna',
    });
    const writer = createOpenAIWriter('test-key');

    await writer.write({
      systemPrompt: 'instrucciones',
      userPrompt: 'pregunta',
      model: 'gpt-6-luna',
      reasoningEffort: 'high',
      requestId: 'chat-test',
      signal: new AbortController().signal,
    });

    expect(createResponse.mock.calls[0]?.[0]).toMatchObject({ max_output_tokens: 4_000 });
    const requestJson = JSON.stringify(createResponse.mock.calls[0]?.[0]);
    expect(requestJson).not.toContain('uniqueItems');
    expect(requestJson).toContain('judicial_assessment');
    expect(requestJson).toContain('procedural_power');
  });

  it('clasifica los errores HTTP de OpenAI sin conservar el mensaje del proveedor', async () => {
    createResponse.mockRejectedValueOnce({
      code: 'rate_limit_exceeded',
      status: 429,
      message: 'The prompt contains datos fiscales privados',
    });
    const writer = createOpenAIWriter('test-key');

    await expect(
      writer.write({
        systemPrompt: 'instrucciones',
        userPrompt: 'pregunta',
        model: 'gpt-6-luna',
        reasoningEffort: 'high',
        requestId: 'chat-test',
        signal: new AbortController().signal,
      })
    ).rejects.toMatchObject({
      constructor: ChatDiagnosticError,
      diagnostic: {
        dependency: 'openai',
        operation: 'responses.create',
        kind: 'provider_error',
        code: 'rate_limit_exceeded',
        status: 429,
        retryable: true,
      },
    });
  });
});

describe('adaptador Gemini de la Function', () => {
  const fetchMock = vi.fn<typeof fetch>();
  const input = {
    model: 'gemini-3.5-flash-lite',
    storeName: 'fileSearchStores/test',
    prompt: 'pregunta privada',
    requestId: 'chat-test',
    metadataFilter: 'judgment_id="san-2132-2025"',
  };
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  const interact = (signal = new AbortController().signal) =>
    createGeminiInteraction('test-key')(input, signal);
  const sentRequest = () => {
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    return { url, init, body: JSON.parse(String(init?.body)) };
  };

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('llama a la API de interacciones con la clave en cabecera y la señal combinada', async () => {
    fetchMock.mockResolvedValueOnce(json({ steps: [] }));

    await interact();

    const { url, init } = sentRequest();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(url).toBe('https://generativelanguage.googleapis.com/v1beta/interactions');
    expect(init).toMatchObject({
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
        'x-goog-api-key': 'test-key',
      },
    });
    expect(String(url)).not.toContain('test-key');
    expect(init?.signal).toBeInstanceOf(AbortSignal);
  });

  it('acota la salida y no envía labels, incompatibles con Gemini API', async () => {
    fetchMock.mockResolvedValueOnce(json({ steps: [] }));

    await interact();

    const { body } = sentRequest();
    expect(body).not.toHaveProperty('labels');
    expect(body).toMatchObject({
      model: 'gemini-3.5-flash-lite',
      input: 'pregunta privada',
      store: false,
      response_format: { type: 'text', mime_type: 'application/json' },
      generation_config: { max_output_tokens: 2_000, tool_choice: 'any' },
      tools: [
        {
          type: 'file_search',
          file_search_store_names: ['fileSearchStores/test'],
          metadata_filter: 'judgment_id="san-2132-2025"',
        },
      ],
    });
  });

  it('devuelve el último tramo de texto como output_text y conserva pasos y uso', async () => {
    const annotations = [{ type: 'file_citation', file_name: 'sentencia.pdf' }];
    const steps = [
      { type: 'user_input', content: [{ type: 'text', text: 'pregunta' }] },
      { type: 'thought', content: [{ type: 'text', text: 'pensando' }] },
      { type: 'model_output', content: [{ type: 'text', text: 'descartado' }] },
      { type: 'file_search_call' },
      {
        type: 'model_output',
        content: [
          { type: 'text', text: '{"a":', annotations },
          { type: 'text', text: '1}' },
        ],
      },
      { type: 'thought', content: [{ type: 'text', text: 'al final' }] },
    ];
    fetchMock.mockResolvedValueOnce(json({ steps, usage: { total_input_tokens: 7 } }));

    await expect(interact()).resolves.toEqual({
      steps,
      usage: { total_input_tokens: 7 },
      output_text: '{"a":1}',
    });
  });

  it('corta output_text en un contenido que no es texto', async () => {
    const steps = [
      {
        type: 'model_output',
        content: [
          { type: 'text', text: 'antes' },
          { type: 'image' },
          { type: 'text', text: 'después' },
        ],
      },
    ];
    fetchMock.mockResolvedValueOnce(json({ steps }));

    await expect(interact()).resolves.toMatchObject({ output_text: 'después' });
  });

  it('normaliza una respuesta sin pasos y respeta el output_text recibido', async () => {
    fetchMock.mockResolvedValueOnce(json({ output_text: 'del servidor' }));

    await expect(interact()).resolves.toEqual({ output_text: 'del servidor', steps: [] });
  });

  it('clasifica los errores de Gemini File Search sin conservar el prompt', async () => {
    fetchMock.mockResolvedValueOnce(
      json(
        {
          error: {
            code: 'UNAVAILABLE',
            message: 'temporary failure for residencia fiscal en Andorra',
          },
        },
        503
      )
    );

    const error = await interact().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ChatDiagnosticError);
    expect(error).toMatchObject({
      message: 'Gemini no disponible',
      diagnostic: {
        dependency: 'gemini',
        operation: 'interactions.create',
        kind: 'provider_error',
        code: 'UNAVAILABLE',
        status: 503,
        retryable: true,
      },
    });
    expect(JSON.stringify(error)).not.toContain('Andorra');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it.each([
    [429, true],
    [400, false],
  ])(
    'marca el estado %i como reintentable=%s aunque el cuerpo no sea JSON',
    async (status, retryable) => {
      fetchMock.mockResolvedValueOnce(new Response('<html>', { status }));

      await expect(interact()).rejects.toMatchObject({
        diagnostic: { kind: 'provider_error', status, retryable },
      });
    }
  );

  it('rechaza un 200 que no es JSON', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('<html>', { status: 200, headers: { 'content-type': 'text/html' } })
    );

    await expect(interact()).rejects.toMatchObject({
      diagnostic: { kind: 'provider_error', status: 200, retryable: false },
    });
  });

  it('rechaza un JSON inválido', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('{no json', { status: 200, headers: { 'content-type': 'application/json' } })
    );

    await expect(interact()).rejects.toMatchObject({
      diagnostic: { dependency: 'gemini', kind: 'provider_error' },
    });
  });

  it('clasifica un fallo de red como error de proveedor', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));

    await expect(interact()).rejects.toMatchObject({
      diagnostic: { kind: 'provider_error', retryable: false },
    });
  });

  const untilAborted: typeof fetch = (_url, init) =>
    new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(init.signal?.reason));
    });

  it('aborta con la señal del llamante como timeout de proveedor', async () => {
    fetchMock.mockImplementationOnce(untilAborted);
    const controller = new AbortController();

    const pending = interact(controller.signal);
    controller.abort();

    await expect(pending).rejects.toMatchObject({
      diagnostic: { kind: 'provider_timeout', retryable: true },
    });
  });

  it('impone 50 s aunque el llamante no aborte', async () => {
    const deadline = new AbortController();
    const timeout = vi.spyOn(AbortSignal, 'timeout').mockReturnValueOnce(deadline.signal);
    fetchMock.mockImplementationOnce(untilAborted);

    const pending = interact();
    deadline.abort(new DOMException('signal timed out', 'TimeoutError'));

    expect(timeout).toHaveBeenCalledWith(50_000);
    await expect(pending).rejects.toMatchObject({
      diagnostic: { kind: 'provider_timeout', retryable: true },
    });
  });
});
