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

import {
  createGeminiInteraction,
  createOpenAIWriter,
} from '../netlify/functions/chat/provider-adapters';

describe('adaptador OpenAI de la Function', () => {
  it('da a Luna high margen de 4.000 tokens para completar el JSON', async () => {
    createResponse.mockResolvedValueOnce({
      output_text: JSON.stringify({
        status: 'pregunta',
        answer: 'Necesito concretar la cuestión.',
        limits: [],
        evidence_ids: [],
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
});
