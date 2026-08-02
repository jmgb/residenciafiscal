import type { SentenciaIndexEntry, SentenciaPublica } from '@/types/sentencias';

/**
 * Rutas, etiquetas y metadatos de las fichas de sentencia.
 *
 * Mismo contrato que las fichas de precepto: el `title` y la `description` que
 * escribe el prerender salen de aquí y de ningún otro sitio, así que el bot y la
 * SPA no pueden discrepar. Y salen **del dato** —órgano, ROJ, ejercicios,
 * criterios—, no de copy escrito por página: con 67 fichas, un texto a mano
 * acabaría en descripciones duplicadas, que es lo que §5.5 prohíbe.
 */

export const SENTENCIAS_INDEX_PATH = '/espana/sentencias';

export function sentenciaPath(judgmentId: string): string {
  return `${SENTENCIAS_INDEX_PATH}/${judgmentId}`;
}

/** Etiquetas de los siete criterios del catálogo (`src/config.py`). */
export const CRITERIO_LABEL: Record<string, string> = {
  CRIT_183_DIAS: 'Permanencia de 183 días',
  CRIT_AUSENCIAS_ESPORADICAS: 'Ausencias esporádicas',
  CRIT_CENTRO_INTERESES_ECONOMICOS: 'Centro de intereses económicos',
  CRIT_CENTRO_INTERESES_VITALES: 'Centro de intereses vitales',
  CRIT_PRESUNCION_FAMILIA: 'Presunción familiar',
  CRIT_CDI_TIEBREAKER: 'Desempate del convenio',
  CRIT_OTRO: 'Otro criterio',
};

/** Etiquetas de los siete resultados de `VALID_RESULTADO_FINAL`. */
export const RESULTADO_LABEL: Record<string, string> = {
  GANA_AEAT: 'Gana la Administración',
  GANA_CONTRIBUYENTE: 'Gana el contribuyente',
  PARCIAL: 'Estimación parcial',
  RETROACCION: 'Retroacción de actuaciones',
  INADMISION: 'Inadmisión',
  OTROS: 'Otro resultado',
  FUERA_DE_ALCANCE: 'Fuera de alcance',
};

export function criterioLabel(criterionId: string): string {
  return CRITERIO_LABEL[criterionId] ?? criterionId;
}

export function resultadoLabel(outcome: string): string {
  return RESULTADO_LABEL[outcome] ?? outcome;
}

/** «Audiencia Nacional, Sala de lo Contencioso…» abreviado para un chip. */
export function organoCorto(court: string): string {
  if (court.startsWith('Tribunal Supremo')) return 'Tribunal Supremo';
  if (court.startsWith('Audiencia Nacional')) return 'Audiencia Nacional';
  return court.split('.')[0] ?? court;
}

export function anio(fecha: string): string {
  return fecha.slice(0, 4);
}

function ejerciciosTexto(taxYears: number[]): string {
  if (taxYears.length === 0) return '';
  if (taxYears.length === 1) return `ejercicio ${taxYears[0]}`;
  const ordenados = [...taxYears].sort((a, b) => a - b);
  return `ejercicios ${ordenados[0]}-${ordenados[ordenados.length - 1]}`;
}

/**
 * Título de la ficha. La entidad va primero y la marca al final, igual que en
 * las fichas de precepto: el ROJ es lo que se busca y lo que debe leerse en el
 * resultado aunque el título se recorte.
 */
export function sentenciaTitle(entry: SentenciaIndexEntry): string {
  const ejercicios = ejerciciosTexto(entry.taxYears);
  const sufijo = ejercicios ? `, ${ejercicios}` : '';
  return `${entry.roj} (${organoCorto(entry.court)}): residencia fiscal${sufijo}`;
}

const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

/** `2017-03-30` → `30 de marzo de 2017`. La fecha ISO no es copy publicable. */
export function fechaLarga(iso: string): string {
  const [anio, mes, dia] = iso.split('-');
  const nombre = MESES[Number(mes) - 1];
  if (!nombre || !dia) return iso;
  return `${Number(dia)} de ${nombre} de ${anio}`;
}

/**
 * Descripción derivada de los criterios y el resultado. Dos sentencias con el
 * mismo ROJ no existen, así que el ROJ garantiza que ninguna descripción se
 * repita en el inventario.
 *
 * Se limita a dos criterios: con cinco —los hay— pasaba de 270 caracteres y el
 * buscador la habría cortado por la mitad.
 */
export const MAX_DESCRIPTION = 180;

export function sentenciaDescription(entry: SentenciaIndexEntry): string {
  const criterios = entry.criterionIds.slice(0, 2).map(criterioLabel).join(' y ');
  const resultados = entry.outcomes.map(resultadoLabel).join(' y ');
  // De más a menos identificativo. Si no cabe todo se cae la coletilla, luego
  // los criterios; el ROJ y el resultado se conservan siempre, porque son lo que
  // distingue una sentencia de otra. Recortar la cadena a mitad de palabra
  // dejaría descripciones truncadas en el buscador.
  const partes = [
    `${entry.roj}, de ${fechaLarga(entry.decisionDate)}`,
    resultados ? `Resultado: ${resultados}` : '',
    criterios ? `Criterios: ${criterios}` : '',
    'Con los extractos literales y su página',
  ].filter(Boolean);

  const elegidas: string[] = [];
  for (const parte of partes) {
    const candidata = `${[...elegidas, parte].join('. ')}.`;
    if (elegidas.length > 0 && candidata.length > MAX_DESCRIPTION) break;
    elegidas.push(parte);
  }
  return `${elegidas.join('. ')}.`;
}

export function sentenciaHeading(entry: SentenciaIndexEntry): string {
  return `${entry.roj} — ${organoCorto(entry.court)}`;
}

/** Entrada de índice equivalente a una ficha, para reusar los metadatos. */
export function entryDeSentencia(sentencia: SentenciaPublica): SentenciaIndexEntry {
  return {
    judgmentId: sentencia.judgment.judgmentId,
    roj: sentencia.judgment.roj,
    court: sentencia.judgment.court,
    decisionDate: sentencia.judgment.decisionDate,
    taxYears: sentencia.judgment.taxYears,
    criterionIds: [...new Set(sentencia.issues.flatMap((issue) => issue.criterionIds))],
    outcomes: [
      ...new Set(
        sentencia.issues.flatMap((issue) => (issue.holding ? [issue.holding.outcome] : []))
      ),
    ],
    jurisdictions: sentencia.jurisdictions.map((jurisdiction) => jurisdiction.code),
    publicationState: sentencia.publicationState,
    legalReview: sentencia.judgment.review.legal,
  };
}

/**
 * Estado de revisión en palabras, para el descargo visible de cada ficha.
 *
 * `AGENT_REVIEWED` **no** puede presentarse como revisión de un experto: el
 * proyecto no afirma que su corpus esté revisado por especialistas, y hay tests
 * que impiden que esa fórmula reaparezca.
 */
export function revisionLabel(legalReview: string): string {
  if (legalReview === 'HUMAN_APPROVED') return 'Análisis aprobado por revisión humana';
  return 'Análisis generado por un modelo, pendiente de revisión humana';
}

/** `true` si la ficha no puede indexarse todavía. */
export function esBorrador(entry: { publicationState: string }): boolean {
  return entry.publicationState !== 'published';
}
