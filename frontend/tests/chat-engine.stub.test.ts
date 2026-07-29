import { describe, expect, it } from 'vitest';
import { createStubChatEngine, pickSources, STUB_TOPICS } from '@/lib/chat-engine.stub';
import type { ChatChunk, ChatMessage, CorpusEntry } from '@/types/chat';

/**
 * Seis sentencias dentro de alcance con criterios decisivos distintos, más una
 * fuera de alcance.
 *
 * El tamaño importa: `pickSources` rellena hasta 4 con las entradas en alcance,
 * así que con solo 3 el relleno se lo tragaba todo y cualquier aserción de
 * pertenencia pasaba aunque la detección de tema no funcionase. Con 6 el
 * `slice(0, 4)` deja fuera entradas y la posición pasa a ser significativa.
 *
 * El orden también importa: la primera entrada en alcance NO es ninguna de las
 * que esperan los tests de tema, de modo que un `detectTopic` roto (que
 * devolviera siempre `null`) los haría fallar.
 */
const corpus: CorpusEntry[] = [
  {
    archivo: 'STS_4305_2017.pdf',
    roj: 'STS 4305/2017',
    ecli: 'ECLI:ES:TS:2017:4305',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo. Sección Segunda',
    fecha: '2017-11-28',
    resultado: 'GANA_AEAT',
    criterioDecisivo: ['CRIT_PRESUNCION_FAMILIA'],
    esCasoResidencia: true,
  },
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
    archivo: 'STS_9999_2019.pdf',
    roj: 'STS 9999/2019',
    ecli: 'ECLI:ES:TS:2019:9999',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
    fecha: '2019-05-05',
    resultado: 'INADMISION',
    criterioDecisivo: [],
    esCasoResidencia: false,
  },
  {
    archivo: 'STS_1129_2020.pdf',
    roj: 'STS 1129/2020',
    ecli: 'ECLI:ES:TS:2020:1129',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo. Sección Segunda',
    fecha: '2020-05-28',
    resultado: 'GANA_AEAT',
    criterioDecisivo: ['CRIT_AUSENCIAS_ESPORADICAS'],
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
    archivo: 'SAN_2534_2023.pdf',
    roj: 'SAN 2534/2023',
    ecli: 'ECLI:ES:AN:2023:2534',
    organo: 'Audiencia Nacional. Sala de lo Contencioso-Administrativo. Sección Cuarta',
    fecha: '2023-06-14',
    resultado: 'GANA_CONTRIBUYENTE',
    criterioDecisivo: ['CRIT_CENTRO_INTERESES_VITALES'],
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
];

const PREGUNTA_DIAS = '¿Cómo se computan los 183 días de permanencia?';
const PREGUNTA_CDI = '¿Cuándo se aplica el convenio de doble imposición?';

function userMessage(content: string): ChatMessage[] {
  return [{ id: 'm1', role: 'user', content, createdAt: '2026-07-29T10:00:00.000Z' }];
}

function textOf(chunks: ChatChunk[]): string {
  return chunks
    .filter((c): c is { type: 'token'; text: string } => c.type === 'token')
    .map((c) => c.text)
    .join('');
}

async function drain(iterable: AsyncIterable<ChatChunk>): Promise<ChatChunk[]> {
  const chunks: ChatChunk[] = [];
  for await (const chunk of iterable) chunks.push(chunk);
  return chunks;
}

describe('pickSources', () => {
  // Se comprueba la POSICIÓN, no la pertenencia: con el relleno hasta 4 fuentes,
  // `toContain` pasaría también con la detección de tema desactivada.
  it('coloca primera la sentencia cuyo criterio decisivo coincide con el tema detectado', () => {
    const sources = pickSources(PREGUNTA_DIAS, corpus);
    expect(sources[0]?.roj).toBe('STS 107/2018');
  });

  it('detecta el tema de CDI y prioriza el tie-breaker', () => {
    const sources = pickSources(PREGUNTA_CDI, corpus);
    expect(sources[0]?.roj).toBe('STS 3942/2021');
  });

  it('antepone todas las coincidencias del tema antes de rellenar', () => {
    const sources = pickSources('¿Dónde se sitúa el centro de intereses económicos?', corpus);
    expect(sources.map((s) => s.roj).slice(0, 2)).toEqual(['SAN 2534/2023', 'SAN 1071/2025']);
  });

  it('nunca devuelve sentencias fuera de alcance', () => {
    const sources = pickSources('cualquier cosa sin palabras clave', corpus);
    expect(sources.every((s) => s.esCasoResidencia)).toBe(true);
  });

  it('nunca devuelve más de 4 fuentes aunque haya más en alcance', () => {
    const sources = pickSources('pregunta genérica', corpus);
    expect(corpus.filter((e) => e.esCasoResidencia).length).toBeGreaterThan(4);
    expect(sources).toHaveLength(4);
  });

  it('devuelve todo el alcance disponible cuando hay menos de 4 sentencias', () => {
    const sources = pickSources('pregunta genérica', corpus.slice(0, 2));
    expect(sources.map((s) => s.roj)).toEqual(['STS 4305/2017', 'STS 107/2018']);
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
    expect(textOf(chunks).toLowerCase()).toContain('simulad');
  });

  it('responde al último mensaje de usuario, no al primero', async () => {
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const history: ChatMessage[] = [
      { id: 'm1', role: 'user', content: PREGUNTA_DIAS, createdAt: '2026-07-29T10:00:00.000Z' },
      {
        id: 'm2',
        role: 'assistant',
        content: 'Respuesta anterior sobre permanencia.',
        createdAt: '2026-07-29T10:00:05.000Z',
      },
      { id: 'm3', role: 'user', content: PREGUNTA_CDI, createdAt: '2026-07-29T10:01:00.000Z' },
    ];

    const chunks = await drain(engine.askQuestion(history, new AbortController().signal));
    const text = textOf(chunks);
    const sourcesChunk = chunks.find((c) => c.type === 'sources');

    expect(text).toContain('tie-breaker');
    expect(text).not.toContain('183 días');
    expect(sourcesChunk?.sources[0]?.roj).toBe('STS 3942/2021');
  });

  it('deja de emitir en cuanto se aborta la señal', async () => {
    const controller = new AbortController();
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks: ChatChunk[] = [];

    for await (const chunk of engine.askQuestion(userMessage('183 días'), controller.signal)) {
      chunks.push(chunk);
      if (chunks.length === 3) controller.abort();
    }

    // Exactamente 3: nada se emite después del abort. La respuesta completa son
    // 141 chunks, así que una cota laxa (`< 20`) no probaría nada.
    expect(chunks).toHaveLength(3);
    expect(chunks.every((c) => c.type === 'token')).toBe(true);
  });

  it('deja de emitir si se aborta durante la espera entre tokens', async () => {
    const controller = new AbortController();
    // Con retardo real (producción usa 18 ms) el abort cae DENTRO del sleep,
    // que es el escenario que `tokenDelayMs: 0` nunca ejercita.
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 5 });
    const chunks: ChatChunk[] = [];
    let timer: ReturnType<typeof setTimeout> | undefined;

    try {
      for await (const chunk of engine.askQuestion(userMessage('183 días'), controller.signal)) {
        chunks.push(chunk);
        // El timer de 0 ms vence antes que el sleep de 5 ms que el generador
        // programa a continuación: el abort llega con el stream en curso.
        if (chunks.length === 3) timer = setTimeout(() => controller.abort(), 0);
      }
    } finally {
      clearTimeout(timer);
    }

    expect(chunks).toHaveLength(3);
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
