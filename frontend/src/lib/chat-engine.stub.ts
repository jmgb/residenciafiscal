/**
 * Implementación SIMULADA del motor de chat.
 *
 * Permanece como modo seguro por defecto aunque el recorrido live ya exista.
 * Emite tokens con retardo para que el streaming, el indicador de escritura y
 * el botón de detener se comporten igual que con el motor real, y enlaza
 * sentencias REALES del corpus para que el panel sea representativo.
 * Sus extractos son resúmenes simulados y se tipan como fuentes históricas:
 * nunca como citas v2 verificadas.
 *
 * Toda respuesta lleva un aviso explícito de que el contenido es simulado: no
 * puede confundirse con análisis jurídico real.
 */
import type {
  ChatChunk,
  ChatEngine,
  ChatMessage,
  CorpusEntry,
  LegacyChatSource,
} from '@/types/chat';

const DISCLAIMER =
  '> **Respuesta simulada.** Esta consulta usa el motor de demostración. ' +
  'El texto siguiente es un ejemplo del formato de respuesta; las sentencias ' +
  'citadas sí son reales y provienen del corpus analizado.\n\n';

export interface StubTopic {
  id: string;
  keywords: string[];
  /** Criterios del pipeline con los que se emparejan las sentencias citadas. */
  criterios: string[];
  answer: string;
}

export const STUB_TOPICS: StubTopic[] = [
  {
    id: 'dias',
    keywords: ['183', 'dias', 'días', 'permanencia', 'computo', 'cómputo', 'estancia'],
    criterios: ['CRIT_183_DIAS', 'CRIT_AUSENCIAS_ESPORADICAS'],
    answer:
      'El cómputo de los **183 días** del art. 9.1.a) LIRPF es el campo de batalla principal: ' +
      'aparece como criterio decisivo en la mayoría de los casos analizados.\n\n' +
      'Los tribunales valoran hechos verificables por encima de formalidades:\n\n' +
      '- **Presencia física acreditada**: sellos de pasaporte, tarjetas de embarque y registros ' +
      'de entrada/salida, siempre que cubran el ejercicio completo y no periodos sueltos.\n' +
      '- **Consumos con patrón continuo**: extractos bancarios y de tarjetas agregados por mes, ' +
      'no tickets aislados.\n' +
      '- **Coherencia temporal**: las contradicciones entre lo alegado y los consumos pesan más ' +
      'que cualquier certificado.\n\n' +
      'La carga de la prueba recae normalmente en quien alega la excepción a la permanencia.',
  },
  {
    id: 'ausencias',
    keywords: ['ausencia', 'ausencias', 'esporadic', 'esporádic', 'temporal'],
    criterios: ['CRIT_AUSENCIAS_ESPORADICAS', 'CRIT_183_DIAS'],
    answer:
      'Las **ausencias esporádicas** del art. 9.1.a), segundo párrafo, LIRPF se computan como ' +
      'permanencia en España salvo que se acredite residencia fiscal en otro país.\n\n' +
      'La doctrina consolidada trata el concepto como **objetivo**: no depende de la intención ' +
      'de volver ni de la duración de la ausencia, sino del dato fáctico de dónde se ha estado ' +
      'y de si existe un certificado de residencia fiscal del otro Estado.\n\n' +
      'Sin ese certificado, las ausencias suman a la permanencia en España.',
  },
  {
    id: 'cdi',
    keywords: [
      'cdi',
      'convenio',
      'doble imposicion',
      'doble imposición',
      'tiebreaker',
      'ocde',
      'desempate',
    ],
    criterios: ['CRIT_CDI_TIEBREAKER'],
    answer:
      'El **tie-breaker del art. 4 del Modelo OCDE** solo entra en juego cuando existe doble ' +
      'residencia real: ambos Estados consideran residente al contribuyente conforme a su ' +
      'normativa interna.\n\n' +
      'El orden de aplicación es escalonado y no se salta pasos:\n\n' +
      '1. Vivienda permanente a disposición.\n' +
      '2. Centro de intereses vitales.\n' +
      '3. Residencia habitual.\n' +
      '4. Nacionalidad.\n' +
      '5. Procedimiento amistoso.\n\n' +
      'Un certificado de residencia fiscal emitido por el otro Estado es condición para abrir ' +
      'el convenio, pero no resuelve por sí solo el desempate.',
  },
  {
    id: 'intereses',
    keywords: [
      'interes',
      'interés',
      'intereses',
      'economic',
      'económic',
      'nucleo',
      'núcleo',
      'vital',
      'centro',
    ],
    criterios: ['CRIT_CENTRO_INTERESES_ECONOMICOS', 'CRIT_CENTRO_INTERESES_VITALES'],
    answer:
      'El **centro de intereses** (art. 9.1.b) LIRPF) entra cuando el cómputo de días no es ' +
      'concluyente o hay doble anclaje.\n\n' +
      'En la vertiente **económica** se compara la localización de las fuentes de renta y del ' +
      'patrimonio gestionado, no solo dónde se tributa. En la vertiente **vital** pesan los ' +
      'vínculos personales y familiares estables.\n\n' +
      'Es un criterio de segunda línea: rara vez decide solo, pero refuerza o desmonta la ' +
      'versión construida sobre la presencia física.',
  },
  {
    id: 'vivienda',
    keywords: ['vivienda', 'domicilio', 'suministro', 'consumo', 'luz', 'agua', 'alquiler'],
    criterios: ['CRIT_183_DIAS', 'CRIT_CENTRO_INTERESES_VITALES'],
    answer:
      'La **vivienda y su uso efectivo** es la categoría probatoria con mejor rendimiento para ' +
      'la Administración en el corpus analizado.\n\n' +
      'Lo que convence a los tribunales no es la titularidad, sino la combinación de:\n\n' +
      '- contrato (propiedad o alquiler) **más** facturas de suministros;\n' +
      '- consumos con coherencia mes a mes;\n' +
      '- contradicciones detectadas, como una vivienda declarada como alquilada a terceros con ' +
      'consumos incompatibles con esa cesión.\n\n' +
      'Disponer de vivienda sin prueba de uso efectivo se admite como indicio, pero raramente decide.',
  },
  {
    id: 'familia',
    keywords: ['familia', 'conyuge', 'cónyuge', 'hijos', 'menores', 'presuncion', 'presunción'],
    criterios: ['CRIT_PRESUNCION_FAMILIA', 'CRIT_CENTRO_INTERESES_VITALES'],
    answer:
      'La **presunción del art. 9.1.b), segundo párrafo, LIRPF** opera cuando el cónyuge no ' +
      'separado legalmente y los hijos menores dependientes residen habitualmente en España.\n\n' +
      'Es una presunción **iuris tantum**: admite prueba en contrario, y desvirtuarla exige ' +
      'acreditar residencia efectiva en otro Estado, no simplemente alegar separación de hecho ' +
      'o desplazamiento laboral.',
  },
];

const FALLBACK_ANSWER =
  'El corpus analizado reúne **106 resoluciones** del Tribunal Supremo y de la Audiencia ' +
  'Nacional sobre residencia fiscal de personas físicas (2015-2025).\n\n' +
  'Puedes preguntar por los criterios del art. 9 LIRPF (permanencia de 183 días, ausencias ' +
  'esporádicas, centro de intereses económicos o vitales, presunción familiar), por las reglas ' +
  'de desempate del art. 4 del Modelo OCDE, o por qué pruebas concretas admiten y rechazan los ' +
  'tribunales.';

const EXTRACTO_POR_RESULTADO: Record<string, string> = {
  GANA_AEAT:
    'El tribunal confirma la residencia fiscal en España y desestima el recurso del contribuyente.',
  GANA_CONTRIBUYENTE:
    'El tribunal estima el recurso: la Administración no acreditó suficientemente la residencia en España.',
  PARCIAL: 'Estimación parcial: el tribunal acoge algunos motivos y rechaza otros.',
  RETROACCION: 'El tribunal ordena retrotraer actuaciones por defectos en la instrucción.',
  INADMISION: 'Recurso inadmitido sin entrar en el fondo del asunto.',
  DESCONOCIDO: 'Resolución del corpus analizado sobre residencia fiscal de personas físicas.',
};

/** Minúsculas sin acentos, para comparar palabras clave de forma robusta. */
function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function detectTopic(question: string): StubTopic | null {
  const haystack = normalize(question);
  let best: { topic: StubTopic; hits: number } | null = null;

  for (const topic of STUB_TOPICS) {
    const hits = topic.keywords.filter((kw) => haystack.includes(normalize(kw))).length;
    if (hits > 0 && (!best || hits > best.hits)) best = { topic, hits };
  }

  return best?.topic ?? null;
}

function toSource(entry: CorpusEntry): LegacyChatSource {
  return {
    ...entry,
    extracto: EXTRACTO_POR_RESULTADO[entry.resultado] ?? EXTRACTO_POR_RESULTADO.DESCONOCIDO,
  };
}

/**
 * Elige entre 2 y 4 sentencias del corpus relevantes para la pregunta.
 * Prioriza las que tienen como criterio decisivo alguno del tema detectado;
 * completa con las más recientes dentro de alcance.
 */
export function pickSources(question: string, corpus: CorpusEntry[]): LegacyChatSource[] {
  const inScope = corpus.filter((entry) => entry.esCasoResidencia);
  if (inScope.length === 0) return [];

  const topic = detectTopic(question);
  const matching = topic
    ? inScope.filter((entry) => entry.criterioDecisivo.some((c) => topic.criterios.includes(c)))
    : [];

  const selected: CorpusEntry[] = [...matching];
  for (const entry of inScope) {
    if (selected.length >= 4) break;
    if (!selected.includes(entry)) selected.push(entry);
  }

  return selected.slice(0, 4).map(toSource);
}

export interface StubEngineOptions {
  /** Retardo entre tokens. 0 en tests para que corran instantáneos. */
  tokenDelayMs?: number;
}

const DEFAULT_TOKEN_DELAY_MS = 18;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Trocea el texto en unidades de token (palabra + espacio) para el streaming. */
function tokenize(text: string): string[] {
  return text.match(/\S+\s*/g) ?? [];
}

export function createStubChatEngine(
  corpus: CorpusEntry[],
  options: StubEngineOptions = {}
): ChatEngine {
  const tokenDelayMs = options.tokenDelayMs ?? DEFAULT_TOKEN_DELAY_MS;

  return {
    async *askQuestion(messages: ChatMessage[], signal: AbortSignal): AsyncIterable<ChatChunk> {
      if (signal.aborted) return;

      const question = [...messages].reverse().find((m) => m.role === 'user')?.content ?? '';
      const topic = detectTopic(question);
      const body = topic?.answer ?? FALLBACK_ANSWER;

      for (const token of tokenize(DISCLAIMER + body)) {
        if (signal.aborted) return;
        if (tokenDelayMs > 0) await sleep(tokenDelayMs);
        if (signal.aborted) return;
        yield { type: 'token', text: token };
      }

      if (signal.aborted) return;
      const sources = pickSources(question, corpus);
      if (sources.length > 0) yield { type: 'sources', sources };

      if (signal.aborted) return;
      yield { type: 'done' };
    },
  };
}
