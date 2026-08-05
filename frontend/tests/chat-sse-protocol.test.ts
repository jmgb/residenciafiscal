import { describe, expect, it } from 'vitest';
import { ChatEngineError, parseChatEventStream } from '@/lib/chat-sse-protocol';
import type { ChatChunk } from '@/types/chat';
import { makeChatSourceV2 } from './chat-source-fixture';

const encoder = new TextEncoder();

function streamFromBytes(parts: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const part of parts) controller.enqueue(part);
      controller.close();
    },
  });
}

function streamFromText(parts: string[]): ReadableStream<Uint8Array> {
  return streamFromBytes(parts.map((part) => encoder.encode(part)));
}

function event(name: string, data: unknown): string {
  return `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
}

async function collect(stream: ReadableStream<Uint8Array>): Promise<ChatChunk[]> {
  const chunks: ChatChunk[] = [];
  for await (const chunk of parseChatEventStream(stream)) chunks.push(chunk);
  return chunks;
}

describe('parseChatEventStream', () => {
  it('acepta un stream con solo la estrategia B activa', async () => {
    const cost = {
      currency: 'USD',
      amount_usd: '0.012345',
      cost_microusd: 12345,
      measurement: 'ACTUAL',
      scope: 'REQUEST_MARGINAL',
      pricing_version: '2026-07-31',
      input_tokens: 8421,
      output_tokens: 631,
      retrieved_document_tokens: 500,
      excludes_corpus_preparation: true,
    };

    await expect(
      collect(
        streamFromText([
          event('answer_start', { strategy: 'gemini_file_search' }),
          event('token', { strategy: 'gemini_file_search', text: 'Respuesta B.' }),
          event('sources', { strategy: 'gemini_file_search', sources: [] }),
          event('answer_done', {
            strategy: 'gemini_file_search',
            status: 'completa',
            limits: [],
            cost,
            model: 'gemini-3.5-flash-lite',
            latency_ms: 900,
          }),
          event('done', { request_id: 'chat-single-b' }),
        ])
      )
    ).resolves.toEqual([
      { type: 'answer_start', strategy: 'gemini_file_search' },
      { type: 'token', strategy: 'gemini_file_search', text: 'Respuesta B.' },
      { type: 'strategy_sources', strategy: 'gemini_file_search', sources: [] },
      {
        type: 'answer_done',
        strategy: 'gemini_file_search',
        status: 'completa',
        limits: [],
        cost: expect.objectContaining({ amountUsd: '0.012345' }),
        model: 'gemini-3.5-flash-lite',
        latencyMs: 900,
      },
      { type: 'done', requestId: 'chat-single-b' },
    ]);
  });

  it('propaga el tipo seguro de fallo de una estrategia', async () => {
    const cost = {
      currency: 'USD',
      amount_usd: '0.001480',
      cost_microusd: 1480,
      measurement: 'ACTUAL',
      scope: 'REQUEST_MARGINAL',
      pricing_version: '2026-07-31',
      input_tokens: 660,
      output_tokens: 169,
      retrieved_document_tokens: 2865,
      excludes_corpus_preparation: true,
    };

    await expect(
      collect(
        streamFromText([
          event('answer_start', { strategy: 'gemini_file_search' }),
          event('sources', { strategy: 'gemini_file_search', sources: [] }),
          event('answer_done', {
            strategy: 'gemini_file_search',
            status: 'error',
            failure_code: 'citation_verification',
            limits: ['Se retiraron citas no verificables contra el PDF original.'],
            cost,
            model: 'gemini-3.5-flash-lite',
            latency_ms: 21809,
          }),
          event('done', { request_id: 'chat-failure-code' }),
        ])
      )
    ).resolves.toContainEqual({
      type: 'answer_done',
      strategy: 'gemini_file_search',
      status: 'error',
      failureCode: 'citation_verification',
      limits: ['Se retiraron citas no verificables contra el PDF original.'],
      cost: expect.objectContaining({ amountUsd: '0.001480' }),
      model: 'gemini-3.5-flash-lite',
      latencyMs: 21809,
    });
  });

  it('mantiene separadas las dos estrategias con sus fuentes, estado y coste', async () => {
    const cost = {
      currency: 'USD',
      amount_usd: '0.012345',
      cost_microusd: 12345,
      measurement: 'ACTUAL',
      scope: 'REQUEST_MARGINAL',
      pricing_version: '2026-07-31',
      input_tokens: 8421,
      output_tokens: 631,
      retrieved_document_tokens: 0,
      excludes_corpus_preparation: true,
    };
    const source = {
      strategy: 'current_structured',
      judgment_id: 'STS-2024-1234',
      page: 7,
      source_sha256: 'a'.repeat(64),
      quote: 'Texto literal de la sentencia.',
      verification: 'EXACT',
    };

    const chunks = await collect(
      streamFromText([
        event('answer_start', { strategy: 'current_structured' }),
        event('token', { strategy: 'current_structured', text: 'Respuesta A.' }),
        event('sources', { strategy: 'current_structured', sources: [source] }),
        event('answer_done', {
          strategy: 'current_structured',
          status: 'completa',
          claims: [{ text: 'Afirmación A.', source_indexes: [1] }],
          limits: [],
          cost,
          model: 'luna',
          latency_ms: 1200,
        }),
        event('answer_start', { strategy: 'gemini_file_search' }),
        event('token', { strategy: 'gemini_file_search', text: 'Respuesta B.' }),
        event('sources', {
          strategy: 'gemini_file_search',
          sources: [{ ...source, strategy: 'gemini_file_search' }],
        }),
        event('answer_done', {
          strategy: 'gemini_file_search',
          status: 'parcial',
          limits: ['Falta contraste.'],
          cost: { ...cost, amount_usd: '0.020000', cost_microusd: 20000 },
          model: 'gemini-2.5-flash',
          latency_ms: 900,
        }),
        event('done', { request_id: 'chat-test' }),
      ])
    );

    expect(chunks).toEqual([
      { type: 'answer_start', strategy: 'current_structured' },
      { type: 'token', strategy: 'current_structured', text: 'Respuesta A.' },
      {
        type: 'strategy_sources',
        strategy: 'current_structured',
        sources: [
          {
            strategy: 'current_structured',
            judgmentId: 'STS-2024-1234',
            page: 7,
            sourceSha256: 'a'.repeat(64),
            quote: 'Texto literal de la sentencia.',
            verification: 'EXACT',
          },
        ],
      },
      {
        type: 'answer_done',
        strategy: 'current_structured',
        status: 'completa',
        claims: [{ text: 'Afirmación A.', sourceIndexes: [1] }],
        limits: [],
        cost: {
          currency: 'USD',
          amountUsd: '0.012345',
          costMicrousd: 12345,
          measurement: 'ACTUAL',
          scope: 'REQUEST_MARGINAL',
          pricingVersion: '2026-07-31',
          inputTokens: 8421,
          outputTokens: 631,
          retrievedDocumentTokens: 0,
          excludesCorpusPreparation: true,
        },
        model: 'luna',
        latencyMs: 1200,
      },
      { type: 'answer_start', strategy: 'gemini_file_search' },
      { type: 'token', strategy: 'gemini_file_search', text: 'Respuesta B.' },
      {
        type: 'strategy_sources',
        strategy: 'gemini_file_search',
        sources: [
          {
            strategy: 'gemini_file_search',
            judgmentId: 'STS-2024-1234',
            page: 7,
            sourceSha256: 'a'.repeat(64),
            quote: 'Texto literal de la sentencia.',
            verification: 'EXACT',
          },
        ],
      },
      {
        type: 'answer_done',
        strategy: 'gemini_file_search',
        status: 'parcial',
        limits: ['Falta contraste.'],
        cost: {
          currency: 'USD',
          amountUsd: '0.020000',
          costMicrousd: 20000,
          measurement: 'ACTUAL',
          scope: 'REQUEST_MARGINAL',
          pricingVersion: '2026-07-31',
          inputTokens: 8421,
          outputTokens: 631,
          retrievedDocumentTokens: 0,
          excludesCorpusPreparation: true,
        },
        model: 'gemini-2.5-flash',
        latencyMs: 900,
      },
      { type: 'done', requestId: 'chat-test' },
    ]);
  });

  it('conserva un coste no disponible sin convertirlo en cero', async () => {
    const unavailable = {
      currency: 'USD',
      amount_usd: null,
      cost_microusd: null,
      measurement: 'UNAVAILABLE',
      scope: 'REQUEST_MARGINAL',
      pricing_version: 'unavailable',
      input_tokens: null,
      output_tokens: null,
      retrieved_document_tokens: null,
      excludes_corpus_preparation: true,
    };
    const blocks = (['current_structured', 'gemini_file_search'] as const).flatMap((strategy) => [
      event('answer_start', { strategy }),
      event('sources', { strategy, sources: [] }),
      event('answer_done', {
        strategy,
        status: 'error',
        limits: ['Proveedor no disponible.'],
        cost: unavailable,
        model: 'unavailable',
        latency_ms: 52_000,
      }),
    ]);

    const chunks = await collect(streamFromText([...blocks, event('done', {})]));

    expect(chunks.filter((chunk) => chunk.type === 'answer_done')).toEqual([
      expect.objectContaining({
        strategy: 'current_structured',
        cost: expect.objectContaining({
          amountUsd: null,
          costMicrousd: null,
          measurement: 'UNAVAILABLE',
        }),
      }),
      expect.objectContaining({
        strategy: 'gemini_file_search',
        cost: expect.objectContaining({
          amountUsd: null,
          costMicrousd: null,
          measurement: 'UNAVAILABLE',
        }),
      }),
    ]);
  });

  it('rechaza tokens comparativos sin estrategia', async () => {
    await expect(
      collect(
        streamFromText([
          event('answer_start', { strategy: 'current_structured' }),
          event('token', { text: 'Sin dueño.' }),
          event('done', {}),
        ])
      )
    ).rejects.toMatchObject({ code: 'invalid_event' });
  });

  it('convierte token, fuentes v2 y done en ChatChunk', async () => {
    const source = makeChatSourceV2();
    const chunks = await collect(
      streamFromText([
        event('token', { text: 'Respuesta.' }),
        event('sources', { sources: [source] }),
        event('done', {}),
      ])
    );

    expect(chunks).toEqual([
      { type: 'token', text: 'Respuesta.' },
      { type: 'sources', sources: [source] },
      { type: 'done' },
    ]);
  });

  it('tolera un evento partido entre varios chunks de red', async () => {
    const chunks = await collect(
      streamFromText(['event: token\ndata: {"te', 'xt":"partido"}\n\n', event('done', {})])
    );

    expect(chunks).toEqual([{ type: 'token', text: 'partido' }, { type: 'done' }]);
  });

  it('preserva un carácter UTF-8 partido entre chunks', async () => {
    const bytes = encoder.encode(`${event('token', { text: 'días' })}${event('done', {})}`);
    const firstContinuationByte = bytes.findIndex((byte) => byte >= 0x80 && byte < 0xc0);
    const chunks = await collect(
      streamFromBytes([bytes.slice(0, firstContinuationByte), bytes.slice(firstContinuationByte)])
    );

    expect(chunks[0]).toEqual({ type: 'token', text: 'días' });
  });

  it('rechaza JSON malformado en vez de ignorarlo', async () => {
    await expect(
      collect(streamFromText(['event: token\ndata: {"text":\n\n', event('done', {})]))
    ).rejects.toMatchObject({
      code: 'invalid_event',
    });
  });

  it('rechaza fuentes legadas o v2 inválidas', async () => {
    const invalid = { ...makeChatSourceV2(), pageIndex: 0 };

    await expect(
      collect(streamFromText([event('sources', { sources: [invalid] }), event('done', {})]))
    ).rejects.toMatchObject({
      code: 'invalid_sources',
    });
  });

  it('rechaza sourceId duplicados en el mismo evento', async () => {
    const source = makeChatSourceV2();

    await expect(
      collect(streamFromText([event('sources', { sources: [source, source] }), event('done', {})]))
    ).rejects.toMatchObject({
      code: 'invalid_sources',
    });
  });

  it('conserva los chunks previos y lanza el error terminal del servidor', async () => {
    const received: ChatChunk[] = [];
    let thrown: unknown;

    try {
      for await (const chunk of parseChatEventStream(
        streamFromText([
          event('token', { text: 'Texto parcial.' }),
          event('error', {
            code: 'upstream_interrupted',
            message: 'La generación se interrumpió.',
            retryable: true,
          }),
        ])
      )) {
        received.push(chunk);
      }
    } catch (error) {
      thrown = error;
    }

    expect(received).toEqual([{ type: 'token', text: 'Texto parcial.' }]);
    expect(thrown).toBeInstanceOf(ChatEngineError);
    expect(thrown).toMatchObject({
      code: 'upstream_interrupted',
      retryable: true,
    });
  });

  it('rechaza EOF sin done ni error', async () => {
    await expect(
      collect(streamFromText([event('token', { text: 'Incompleta.' })]))
    ).rejects.toMatchObject({
      code: 'stream_truncated',
    });
  });

  it('tipa un corte de red después de conservar los chunks recibidos', async () => {
    const partial = encoder.encode(event('token', { text: 'Texto parcial.' }));
    let delivered = false;
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (!delivered) {
          delivered = true;
          controller.enqueue(partial);
          return;
        }
        controller.error(new TypeError('network stream failed'));
      },
    });
    const received: ChatChunk[] = [];
    let thrown: unknown;

    try {
      for await (const chunk of parseChatEventStream(stream)) received.push(chunk);
    } catch (error) {
      thrown = error;
    }

    expect(received).toEqual([{ type: 'token', text: 'Texto parcial.' }]);
    expect(thrown).toMatchObject({
      code: 'stream_interrupted',
      retryable: true,
    });
  });

  it('rechaza eventos desconocidos', async () => {
    await expect(
      collect(streamFromText([event('misterioso', {}), event('done', {})]))
    ).rejects.toMatchObject({
      code: 'unexpected_event',
    });
  });

  it('rechaza un terminal done con payload inesperado', async () => {
    await expect(
      collect(streamFromText([event('done', { resultado: 'oculto' })]))
    ).rejects.toMatchObject({
      code: 'invalid_event',
    });
  });

  it('rechaza cualquier evento posterior a done', async () => {
    await expect(
      collect(streamFromText([event('done', {}), event('token', { text: 'tardío' })]))
    ).rejects.toMatchObject({
      code: 'event_after_terminal',
    });
  });
});
