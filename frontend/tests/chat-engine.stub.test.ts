import { describe, expect, it } from 'vitest';
import { createStubChatEngine, pickSources, STUB_TOPICS } from '@/lib/chat-engine.stub';
import type { ChatChunk, ChatMessage, CorpusEntry } from '@/types/chat';

const corpus: CorpusEntry[] = [
  {
    archivo: 'STS_107_2018.pdf',
    roj: 'STS 107/2018',
    ecli: 'ECLI:ES:TS:2018:107',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
    fecha: '2018-01-16',
    resultado: 'GANA_AEAT',
    criterioDecisivo: ['CRIT_183_DIAS'],
    esCasoResidencia: true,
  },
  {
    archivo: 'STS_3942_2021.pdf',
    roj: 'STS 3942/2021',
    ecli: 'ECLI:ES:TS:2021:3942',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
    fecha: '2021-11-04',
    resultado: 'GANA_CONTRIBUYENTE',
    criterioDecisivo: ['CRIT_CDI_TIEBREAKER'],
    esCasoResidencia: true,
  },
  {
    archivo: 'SAN_1071_2025.pdf',
    roj: 'SAN 1071/2025',
    ecli: 'ECLI:ES:AN:2025:1071',
    organo: 'Audiencia Nacional. Sala de lo Contencioso-Administrativo',
    fecha: '2025-02-18',
    resultado: 'PARCIAL',
    criterioDecisivo: ['CRIT_CENTRO_INTERESES_ECONOMICOS'],
    esCasoResidencia: true,
  },
  {
    archivo: 'STS_9999_2019.pdf',
    roj: 'STS 9999/2019',
    ecli: 'ECLI:ES:TS:2019:9999',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
    fecha: '2019-05-05',
    resultado: 'INADMISION',
    criterioDecisivo: [],
    esCasoResidencia: false,
  },
];

function userMessage(content: string): ChatMessage[] {
  return [{ id: 'm1', role: 'user', content, createdAt: '2026-07-29T10:00:00.000Z' }];
}

async function drain(iterable: AsyncIterable<ChatChunk>): Promise<ChatChunk[]> {
  const chunks: ChatChunk[] = [];
  for await (const chunk of iterable) chunks.push(chunk);
  return chunks;
}

describe('pickSources', () => {
  it('selecciona sentencias cuyo criterio decisivo coincide con el tema detectado', () => {
    const sources = pickSources('¿Cómo se computan los 183 días de permanencia?', corpus);
    expect(sources.map((s) => s.roj)).toContain('STS 107/2018');
  });

  it('detecta el tema de CDI y prioriza el tie-breaker', () => {
    const sources = pickSources('¿Cuándo se aplica el convenio de doble imposición?', corpus);
    expect(sources.map((s) => s.roj)).toContain('STS 3942/2021');
  });

  it('nunca devuelve sentencias fuera de alcance', () => {
    const sources = pickSources('cualquier cosa sin palabras clave', corpus);
    expect(sources.every((s) => s.esCasoResidencia)).toBe(true);
  });

  it('devuelve entre 2 y 4 fuentes aunque no haya coincidencias', () => {
    const sources = pickSources('pregunta genérica', corpus);
    expect(sources.length).toBeGreaterThanOrEqual(2);
    expect(sources.length).toBeLessThanOrEqual(4);
  });

  it('adjunta un extracto no vacío a cada fuente', () => {
    const sources = pickSources('183 días', corpus);
    expect(sources.every((s) => s.extracto.length > 0)).toBe(true);
  });

  it('con un corpus vacío devuelve una lista vacía', () => {
    expect(pickSources('183 días', [])).toEqual([]);
  });
});

describe('createStubChatEngine', () => {
  it('emite tokens, después fuentes y termina con done', async () => {
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks = await drain(
      engine.askQuestion(userMessage('¿Y los 183 días?'), new AbortController().signal)
    );

    expect(chunks.filter((c) => c.type === 'token').length).toBeGreaterThan(0);
    expect(chunks.at(-1)).toEqual({ type: 'done' });

    const sourcesChunk = chunks.find((c) => c.type === 'sources');
    expect(sourcesChunk).toBeDefined();
  });

  it('el texto concatenado incluye el aviso de motor simulado', async () => {
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks = await drain(
      engine.askQuestion(userMessage('183 días'), new AbortController().signal)
    );
    const text = chunks
      .filter((c): c is { type: 'token'; text: string } => c.type === 'token')
      .map((c) => c.text)
      .join('');

    expect(text.toLowerCase()).toContain('simulad');
  });

  it('deja de emitir cuando se aborta la señal', async () => {
    const controller = new AbortController();
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks: ChatChunk[] = [];

    for await (const chunk of engine.askQuestion(userMessage('183 días'), controller.signal)) {
      chunks.push(chunk);
      if (chunks.length === 3) controller.abort();
    }

    expect(chunks.length).toBeLessThan(20);
    expect(chunks.at(-1)).not.toEqual({ type: 'done' });
  });

  it('no emite nada si la señal ya viene abortada', async () => {
    const controller = new AbortController();
    controller.abort();
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks = await drain(engine.askQuestion(userMessage('183 días'), controller.signal));

    expect(chunks).toEqual([]);
  });

  it('cada tema declarado tiene una respuesta no vacía', () => {
    for (const topic of STUB_TOPICS) {
      expect(topic.answer.trim().length).toBeGreaterThan(0);
      expect(topic.keywords.length).toBeGreaterThan(0);
    }
  });
});
