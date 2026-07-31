import { describe, expect, it, vi } from 'vitest';
import corpus from '../../knowledge/jurisprudencia-v3/retrieval/corpus.json';
import {
  CurrentStructuredStrategy,
  type StructuredWriter,
} from '../netlify/functions/chat/current-structured-strategy';
import { GeminiFileSearchStrategy } from '../netlify/functions/chat/file-search-strategy';

const context = { requestId: 'chat-test', signal: new AbortController().signal };

describe('estrategia A estructurada', () => {
  it('resuelve IDs opacos a citas exactas del corpus y contabiliza el uso', async () => {
    const write = vi.fn(async (_input: Parameters<StructuredWriter['write']>[0]) => ({
      draft: {
        status: 'completa' as const,
        answer: 'La Sala valoró un conjunto de indicios.',
        limits: ['Muestra piloto de cinco sentencias.'],
        evidence_ids: ['E1'],
      },
      usage: { input_tokens: 100, output_tokens: 40, complete: true },
      model: 'gpt-5.6-luna',
    }));
    const strategy = new CurrentStructuredStrategy(corpus, { write });

    const answer = await strategy.answer(
      '¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?',
      context
    );

    expect(write).toHaveBeenCalledOnce();
    expect(write.mock.calls[0]?.[0]).toMatchObject({
      model: 'gpt-5.6-luna',
      reasoningEffort: 'high',
    });
    const writerInput = write.mock.calls[0]?.[0];
    if (!writerInput) throw new Error('El redactor no recibió contexto');
    expect(
      new TextEncoder().encode(`${writerInput.systemPrompt}\n${writerInput.userPrompt}`).byteLength
    ).toBeLessThanOrEqual(48 * 1024);
    const contextJson = writerInput.userPrompt.split('Contexto estructurado recuperado:\n')[1];
    const packed = JSON.parse(contextJson ?? '{}') as { units?: unknown[] };
    for (const unit of packed.units ?? []) {
      expect(new TextEncoder().encode(JSON.stringify(unit)).byteLength).toBeLessThanOrEqual(
        4 * 1024
      );
    }
    expect(answer).toMatchObject({
      strategy: 'current_structured',
      status: 'completa',
      model: 'gpt-5.6-luna',
      sources: [{ strategy: 'current_structured', verification: 'EXACT' }],
      cost: {
        measurement: 'ACTUAL',
        input_tokens: 100,
        output_tokens: 40,
        retrieved_document_tokens: 0,
      },
    });
  });

  it('retira una respuesta sustantiva si el redactor inventa IDs de evidencia', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'completa',
          answer: 'No debe publicarse.',
          limits: [],
          evidence_ids: ['E999'],
        },
        usage: { input_tokens: 10, output_tokens: 10, complete: true },
        model: 'gpt-5.6-luna',
      }),
    });

    const answer = await strategy.answer(
      '¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?',
      context
    );

    expect(answer).toMatchObject({ status: 'error', text: '', sources: [] });
    expect(answer.limits.join(' ')).toContain('E999');
  });

  it('no llama al LLM cuando debe preguntar o abstenerse', async () => {
    const write = vi.fn();
    const strategy = new CurrentStructuredStrategy(corpus, { write });

    const answer = await strategy.answer(
      '¿Qué son las ausencias esporádicas y cuándo computan?',
      context
    );

    expect(write).not.toHaveBeenCalled();
    expect(answer).toMatchObject({ status: 'abstención', cost: { cost_microusd: 0 } });
  });
});

describe('estrategia B Gemini File Search', () => {
  const artifact = {
    judgment_id: 'sentencia-1',
    source_sha256: 'a'.repeat(64),
    pages: [{ page_index: 1, raw_page_text: 'La Sala valora conjuntamente toda la prueba.' }],
  };

  it('solo publica citas verificadas contra el texto íntegro local', async () => {
    const interact = vi.fn(async () => ({
      output_text: JSON.stringify({
        status: 'completa',
        answer: 'La valoración es conjunta.',
        limits: [],
      }),
      steps: [
        {
          type: 'model_output',
          content: [
            {
              annotations: [
                {
                  type: 'file_citation',
                  page_number: 1,
                  source: 'valora conjuntamente toda la prueba',
                  custom_metadata: {
                    judgment_id: 'sentencia-1',
                    source_sha256: 'a'.repeat(64),
                  },
                },
              ],
            },
          ],
        },
      ],
      usage: {
        total_input_tokens: 120,
        total_output_tokens: 20,
        total_thought_tokens: 30,
        input_tokens_by_modality: [{ modality: 'document', tokens: 100 }],
      },
    }));
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'sentencia-1': artifact },
      interact,
    });

    const answer = await strategy.answer('¿Qué valoró la Sala?', context);

    expect(interact).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'gemini-3.5-flash-lite',
        storeName: 'fileSearchStores/test',
        requestId: 'chat-test',
      }),
      context.signal
    );
    expect(answer).toMatchObject({
      status: 'completa',
      sources: [
        {
          judgment_id: 'sentencia-1',
          page: 1,
          quote: 'valora conjuntamente toda la prueba',
          verification: 'EXACT',
        },
      ],
      cost: {
        measurement: 'ACTUAL',
        input_tokens: 20,
        retrieved_document_tokens: 100,
        output_tokens: 50,
      },
    });
  });

  it('retira una respuesta sustantiva sin citas verificables', async () => {
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'sentencia-1': artifact },
      interact: async () => ({
        output_text: JSON.stringify({ status: 'completa', answer: 'Sin respaldo.', limits: [] }),
        steps: [],
        usage: {
          total_input_tokens: 5,
          total_output_tokens: 5,
          total_thought_tokens: 0,
          input_tokens_by_modality: [],
        },
      }),
    });

    const answer = await strategy.answer('¿Qué valoró la Sala?', context);

    expect(answer).toMatchObject({ status: 'error', text: '', sources: [] });
    expect(answer.limits.join(' ')).toContain('no devolvió citas verificables');
  });
});
