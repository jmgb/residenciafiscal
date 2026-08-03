import { describe, expect, it, vi } from 'vitest';

const { createInteraction, createResponse } = vi.hoisted(() => ({
  createInteraction: vi.fn(),
  createResponse: vi.fn(),
}));

vi.mock('@google/genai', () => ({
  GoogleGenAI: class GoogleGenAI {
    interactions = { create: createInteraction };
  },
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
      model: 'gpt-5.6-luna',
    });
    const writer = createOpenAIWriter('test-key');

    await writer.write({
      systemPrompt: 'instrucciones',
      userPrompt: 'pregunta',
      model: 'gpt-5.6-luna',
      reasoningEffort: 'high',
      requestId: 'chat-test',
      signal: new AbortController().signal,
    });

    expect(createResponse.mock.calls[0]?.[0]).toMatchObject({ max_output_tokens: 4_000 });
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
        model: 'gpt-5.6-luna',
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
  it('acota la salida y no envía labels, incompatibles con Gemini API', async () => {
    createInteraction.mockResolvedValueOnce({ output_text: '{}' });
    const interact = createGeminiInteraction('test-key');

    await interact(
      {
        model: 'gemini-3.5-flash-lite',
        storeName: 'fileSearchStores/test',
        prompt: 'pregunta',
        requestId: 'chat-test',
        metadataFilter: 'judgment_id="san-2132-2025"',
      },
      new AbortController().signal
    );

    expect(createInteraction.mock.calls[0]?.[0]).not.toHaveProperty('labels');
    expect(createInteraction.mock.calls[0]?.[0]).toMatchObject({
      generation_config: { max_output_tokens: 2_000 },
      tools: [expect.objectContaining({ metadata_filter: 'judgment_id="san-2132-2025"' })],
    });
  });

  it('clasifica los errores de Gemini File Search sin conservar el prompt', async () => {
    createInteraction.mockRejectedValueOnce({
      code: 'UNAVAILABLE',
      status: 503,
      message: 'temporary failure for residencia fiscal en Andorra',
    });
    const interact = createGeminiInteraction('test-key');

    await expect(
      interact(
        {
          model: 'gemini-3.5-flash-lite',
          storeName: 'fileSearchStores/test',
          prompt: 'pregunta privada',
          requestId: 'chat-test',
        },
        new AbortController().signal
      )
    ).rejects.toMatchObject({
      constructor: ChatDiagnosticError,
      diagnostic: {
        dependency: 'gemini',
        operation: 'interactions.create',
        kind: 'provider_error',
        code: 'UNAVAILABLE',
        status: 503,
        retryable: true,
      },
    });
  });
});
