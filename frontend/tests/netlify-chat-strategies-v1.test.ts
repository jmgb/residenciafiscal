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
        claims: [
          {
            kind: 'party_argument' as const,
            text: 'La actuaria realizó un seguimiento de las cuentas bancarias.',
            evidence_ids: ['E1'],
          },
        ],
        limits: ['Muestra piloto de cinco sentencias.'],
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
    expect(writerInput.systemPrompt).toContain('La primera claim debe contestar directamente');
    expect(writerInput.systemPrompt).toContain('Si la pregunta contiene varias partes');
    expect(writerInput.systemPrompt).toContain(
      'no equivale por sí solo a presencia física en una fecha'
    );
    expect(writerInput.systemPrompt).toContain(
      'una parte carece de respaldo, no crees una claim para esa parte'
    );
    expect(writerInput.systemPrompt).toContain(
      'distingue obligatoriamente los medios utilizados o alegados, su valoración judicial y el resultado probatorio'
    );
    expect(writerInput.systemPrompt).toContain(
      'No relegues una insuficiencia probatoria decisiva al campo limits'
    );
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
      text: '- La actuaria realizó un seguimiento de las cuentas bancarias. [1]',
      claims: [
        {
          text: 'La actuaria realizó un seguimiento de las cuentas bancarias.',
          source_indexes: [1],
        },
      ],
      model: 'gpt-5.6-luna',
      reasoning_effort: 'high',
      sources: [{ strategy: 'current_structured', verification: 'EXACT' }],
      cost: {
        measurement: 'ACTUAL',
        input_tokens: 100,
        output_tokens: 40,
        retrieved_document_tokens: 0,
      },
    });
    expect(answer.limits).not.toContain('ejercicio');
    expect(answer.limits).not.toContain('país o países implicados');
  });

  it('retira una respuesta sustantiva si el redactor inventa IDs de evidencia', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'completa',
          claims: [{ kind: 'party_argument', text: 'No debe publicarse.', evidence_ids: ['E999'] }],
          limits: [],
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

  it('retira una respuesta si alguna afirmación sustantiva queda sin evidencia', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'completa',
          claims: [
            { kind: 'party_argument', text: 'Afirmación respaldada.', evidence_ids: ['E1'] },
            { kind: 'party_argument', text: 'Afirmación sin respaldo.', evidence_ids: [] },
          ],
          limits: [],
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
    expect(answer.limits.join(' ')).toContain('sin evidencia');
  });

  it('retira afirmaciones cuyo contenido no guarda relación léxica con sus citas', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'completa',
          claims: [
            {
              kind: 'party_argument',
              text: 'La jurisprudencia valida una colonia permanente en la Luna.',
              evidence_ids: ['E1'],
            },
          ],
          limits: [],
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
    expect(answer.limits.join(' ')).toContain('relación suficiente');
  });

  it('no permite presentar una alegación como valoración judicial', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'completa',
          claims: [
            {
              kind: 'judicial_assessment',
              text: 'La actuaria realizó un seguimiento de las cuentas bancarias.',
              evidence_ids: ['E1'],
            },
          ],
          limits: [],
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
    expect(answer.limits.join(' ')).toContain('función jurídica');
  });

  it('conserva las afirmaciones respaldadas y degrada a parcial si retira otra', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'completa',
          claims: [
            {
              kind: 'party_argument',
              text: 'La actuaria realizó un seguimiento de las cuentas bancarias.',
              evidence_ids: ['E1'],
            },
            {
              kind: 'party_argument',
              text: 'La jurisprudencia valida una colonia permanente en la Luna.',
              evidence_ids: ['E1'],
            },
          ],
          limits: [],
        },
        usage: { input_tokens: 10, output_tokens: 10, complete: true },
        model: 'gpt-5.6-luna',
      }),
    });

    const answer = await strategy.answer(
      '¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?',
      context
    );

    expect(answer).toMatchObject({
      status: 'parcial',
      text: '- La actuaria realizó un seguimiento de las cuentas bancarias. [1]',
      claims: [
        {
          text: 'La actuaria realizó un seguimiento de las cuentas bancarias.',
          source_indexes: [1],
        },
      ],
    });
    expect(answer.text).not.toContain('Luna');
    expect(answer.limits.join(' ')).toContain('Se retiró 1 afirmación');
  });

  it('permite que el redactor se abstenga sin inventar afirmaciones ni evidencias', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'abstención',
          claims: [],
          limits: ['Los extractos recuperados no bastan para responder.'],
        },
        usage: { input_tokens: 10, output_tokens: 10, complete: true },
        model: 'gpt-5.6-luna',
      }),
    });

    const answer = await strategy.answer(
      '¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?',
      context
    );

    expect(answer).toMatchObject({
      status: 'abstención',
      text: '',
      sources: [],
      claims: [],
      limits: ['Los extractos recuperados no bastan para responder.'],
    });
  });

  it('normaliza IDs repetidos antes de exponer los índices de cita', async () => {
    const strategy = new CurrentStructuredStrategy(corpus, {
      write: async () => ({
        draft: {
          status: 'completa',
          claims: [
            {
              kind: 'party_argument',
              text: 'La actuaria realizó un seguimiento de las cuentas bancarias.',
              evidence_ids: ['E1', 'E1'],
            },
          ],
          limits: [],
        },
        usage: { input_tokens: 10, output_tokens: 10, complete: true },
        model: 'gpt-5.6-luna',
      }),
    });

    const answer = await strategy.answer(
      '¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?',
      context
    );

    expect(answer.claims).toEqual([
      {
        text: 'La actuaria realizó un seguimiento de las cuentas bancarias.',
        source_indexes: [1],
      },
    ]);
  });

  it('no llama al LLM cuando debe preguntar o abstenerse', async () => {
    const write = vi.fn();
    const strategy = new CurrentStructuredStrategy(corpus, { write });

    const answer = await strategy.answer(
      '¿Qué son las ausencias esporádicas y cuándo computan?',
      context
    );

    expect(write).not.toHaveBeenCalled();
    expect(answer).toMatchObject({
      status: 'abstención',
      reasoning_effort: null,
      cost: { cost_microusd: 0 },
    });
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
        input_tokens_by_modality: [{ modality: 'text', tokens: 120 }],
        total_tool_use_tokens: 100,
        tool_use_tokens_by_modality: [{ modality: 'text', tokens: 100 }],
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
      reasoning_effort: null,
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
        input_tokens: 120,
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
        steps: [
          {
            type: 'model_output',
            content: [
              {
                annotations: [
                  {
                    type: 'file_citation',
                    page_number: 1,
                    source: 'Texto que no existe en el PDF.',
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
          total_input_tokens: 5,
          total_output_tokens: 5,
          total_thought_tokens: 0,
          input_tokens_by_modality: [],
        },
      }),
    });

    const answer = await strategy.answer('¿Qué valoró la Sala?', context);

    expect(answer).toMatchObject({ status: 'error', text: '', sources: [] });
    expect(answer.limits.join(' ')).toContain('citas no verificables');
    expect(answer.diagnostics).toMatchObject({
      citation_candidates: 1,
      citation_verified: 0,
      failure_code: 'citation_verification',
    });
  });

  it('reintenta una vez con el mismo proveedor si la primera cita no es verificable', async () => {
    const usage = {
      total_input_tokens: 5,
      total_output_tokens: 5,
      total_thought_tokens: 0,
      input_tokens_by_modality: [],
    };
    const interact = vi
      .fn()
      .mockResolvedValueOnce({
        output_text: JSON.stringify({ status: 'parcial', answer: 'Primer intento.', limits: [] }),
        steps: [],
        usage,
      })
      .mockResolvedValueOnce({
        output_text: JSON.stringify({ status: 'parcial', answer: 'Segundo intento.', limits: [] }),
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
        usage,
      });
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'sentencia-1': artifact },
      interact,
    });

    const answer = await strategy.answer('¿Qué valoró la Sala?', context);

    expect(interact).toHaveBeenCalledTimes(2);
    expect(interact.mock.calls[1]?.[0].prompt).toContain('segundo y último intento');
    expect(answer).toMatchObject({
      status: 'parcial',
      text: 'Segundo intento.',
      sources: [{ judgment_id: 'sentencia-1' }],
      cost: { input_tokens: 10, output_tokens: 10 },
    });
  });

  it('conserva el coste del primer intento si el reintento del proveedor falla', async () => {
    const interact = vi
      .fn()
      .mockResolvedValueOnce({
        output_text: JSON.stringify({ status: 'parcial', answer: 'Sin cita.', limits: [] }),
        steps: [],
        usage: {
          total_input_tokens: 7,
          total_output_tokens: 3,
          total_thought_tokens: 0,
          input_tokens_by_modality: [],
        },
      })
      .mockRejectedValueOnce(new Error('fallo del segundo intento'));
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'sentencia-1': artifact },
      interact,
    });

    const answer = await strategy.answer('¿Qué valoró la Sala?', context);

    expect(interact).toHaveBeenCalledTimes(2);
    expect(answer).toMatchObject({
      status: 'error',
      text: '',
      cost: { input_tokens: 7, output_tokens: 3 },
      diagnostics: { failure_code: 'citation_verification' },
    });
  });

  it('filtra por metadata cuando la pregunta identifica una única sentencia', async () => {
    const interact = vi.fn(async () => ({
      output_text: JSON.stringify({ status: 'abstención', answer: '', limits: [] }),
      steps: [],
      usage: {
        total_input_tokens: 5,
        total_output_tokens: 5,
        total_thought_tokens: 0,
        input_tokens_by_modality: [],
      },
    }));
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'sentencia-1': artifact },
      interact,
    });

    await strategy.answer('¿Qué resolvió la SAN 2132/2025?', context);

    expect(interact).toHaveBeenCalledWith(
      expect.objectContaining({ metadataFilter: 'judgment_id="san-2132-2025"' }),
      context.signal
    );
  });

  it('filtra por metadata de autoridad cuando se pide doctrina del Tribunal Supremo', async () => {
    const interact = vi.fn(async () => ({
      output_text: JSON.stringify({ status: 'abstención', answer: '', limits: [] }),
      steps: [],
      usage: {
        total_input_tokens: 5,
        total_output_tokens: 5,
        total_thought_tokens: 0,
        input_tokens_by_modality: [],
      },
    }));
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'sentencia-1': artifact },
      interact,
    });

    await strategy.answer(
      '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
      context
    );

    expect(interact).toHaveBeenCalledWith(
      expect.objectContaining({ metadataFilter: 'authority="tribunal_supremo"' }),
      context.signal
    );
    expect(JSON.stringify(interact.mock.calls)).toContain(
      'no concluyas que el corpus carece de documentos'
    );
    expect(JSON.stringify(interact.mock.calls)).toContain(
      'Responde primero y de forma directa a lo preguntado'
    );
    expect(JSON.stringify(interact.mock.calls)).toContain(
      'No desarrolles dimensiones que la pregunta no necesita'
    );
    expect(JSON.stringify(interact.mock.calls)).toContain(
      'No atribuyas al tribunal argumentos de las partes'
    );
    expect(JSON.stringify(interact.mock.calls)).toContain('intención de retorno');
    expect(JSON.stringify(interact.mock.calls)).toContain(
      'contesta cada parte o usa estado parcial'
    );
    expect(JSON.stringify(interact.mock.calls)).toContain(
      'No equipares desvirtuar el número de días'
    );
    expect(JSON.stringify(interact.mock.calls)).toContain('limits contiene solo carencias reales');
    expect(JSON.stringify(interact.mock.calls)).toContain(
      'expresa de forma explícita la condición y sus excepciones'
    );
  });

  it('distingue alta o cuota de uso efectivo en preguntas sobre gimnasio y móvil', async () => {
    const interact = vi.fn(async () => ({
      output_text: JSON.stringify({
        status: 'abstención',
        answer: '',
        limits: ['No se recuperó evidencia suficiente.'],
      }),
      steps: [],
      usage: {
        total_input_tokens: 5,
        total_output_tokens: 5,
        total_thought_tokens: 0,
        input_tokens_by_modality: [],
      },
    }));
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'sentencia-1': artifact },
      interact,
    });

    await strategy.answer(
      'si una persona se apunta al gym o si usa su teléfono movil en españa, ¿la AEAT lo tiene en cuenta para los 183 días?',
      context
    );

    const serializedCall = JSON.stringify(interact.mock.calls);
    expect(serializedCall).toContain('al menos un pasaje citado por File Search');
    expect(serializedCall).toContain('alta, titularidad o pago de una cuota');
    expect(serializedCall).toContain('uso efectivo atribuible al contribuyente');
    expect(serializedCall).toContain('cada parte por separado');
    expect(serializedCall).toContain('gym” equivale a “gimnasio”');
    expect(serializedCall).toContain('cuotas de clubs deportivos');
    expect(serializedCall).toContain('busca por separado la frase exacta');
    expect(serializedCall).toContain('responde de forma parcial sobre el gimnasio');
    expect(serializedCall).toContain('no presupone geolocalización');
  });

  it('degrada una respuesta completa si no cita directamente la autoridad solicitada', async () => {
    const sanArtifact = {
      judgment_id: 'san-1-2024',
      source_sha256: 'b'.repeat(64),
      pages: [{ page_index: 1, raw_page_text: 'La Audiencia Nacional valora la prueba.' }],
    };
    const strategy = new GeminiFileSearchStrategy({
      storeName: 'fileSearchStores/test',
      artifacts: { 'san-1-2024': sanArtifact },
      interact: async () => ({
        output_text: JSON.stringify({
          status: 'completa',
          answer: 'El Tribunal Supremo acepta esta prueba.',
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
                    source: 'La Audiencia Nacional valora la prueba.',
                    custom_metadata: {
                      judgment_id: 'san-1-2024',
                      source_sha256: 'b'.repeat(64),
                    },
                  },
                ],
              },
            ],
          },
        ],
        usage: {
          total_input_tokens: 20,
          total_output_tokens: 10,
          input_tokens_by_modality: [{ modality: 'document', tokens: 10 }],
        },
      }),
    });

    const answer = await strategy.answer(
      '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
      context
    );

    expect(answer.status).toBe('parcial');
    expect(answer.limits.join(' ')).toContain('Tribunal Supremo');
    expect(answer.diagnostics).toMatchObject({
      authority_intent: 'tribunal_supremo',
      authority_match: 'missing',
      citation_candidates: 1,
      citation_verified: 1,
      failure_code: null,
    });
  });
});
