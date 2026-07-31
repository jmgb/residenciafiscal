import type { QueryAnalysis, RetrievalCorpus } from './retrieval-types';

const facets: Array<[string, string[]]> = [
  ['CRIT_AUSENCIAS_ESPORADICAS', ['ausencias esporadicas']],
  ['CRIT_183_DIAS', ['183', 'dias', 'calendario', 'pasaporte', 'billete', 'reserva']],
  [
    'CRIT_CENTRO_INTERESES_ECONOMICOS',
    ['centro economico', 'intereses economicos', 'ingresos', 'rentas', 'sociedad', 'consej'],
  ],
  ['CRIT_PRESUNCION_FAMILIAR', ['familia', 'pareja', 'conyuge', 'hijo', 'presuncion familiar']],
  ['CRIT_CDI_TIEBREAKER', ['convenio', 'cdi', 'dos paises', 'ambos paises', 'vivienda permanente']],
];
const evidence: Array<[string, string[]]> = [
  ['PRESENCIA_FISICA_Y_DESPLAZAMIENTOS', ['dias', 'pasaporte', 'billete', 'viaje', 'reserva']],
  ['VIVIENDA_Y_USO_EFECTIVO', ['vivienda', 'casa', 'alquiler', 'domicilio']],
  [
    'SUMINISTROS_Y_CONSUMOS_DOMESTICOS',
    ['electricidad', 'agua', 'gas', 'gasoleo', 'suministro', 'paqueteria', 'combustible'],
  ],
  ['CONSUMOS_FINANCIEROS', ['tarjeta', 'pago', 'retirada', 'consumo', 'movimiento']],
  ['FAMILIA_Y_ENTORNO_PERSONAL', ['familia', 'pareja', 'conyuge', 'hijo']],
  ['SALUD_Y_SERVICIOS_PERSONALES', ['salud', 'medic', 'discapacidad']],
  [
    'ACTIVIDAD_ECONOMICA_Y_GESTION',
    ['empleo', 'trabajo', 'sociedad', 'consej', 'ingresos', 'rentas', 'inversion'],
  ],
  [
    'DOCUMENTACION_FISCAL_EXTRANJERA',
    ['certificado', 'documentacion extranjera', 'residencia emitido', 'declaracion'],
  ],
];
const factDimensions: Array<[string, string[]]> = [
  ['ejercicio', ['ejercicio', 'ano', '201', '202']],
  ['país o países implicados', ['francia', 'suiza', 'monaco', 'portugal', 'reino unido']],
  ['calendario de presencia', ['dias', '183', '170', 'calendario']],
  ['familia', ['familia', 'pareja', 'conyuge', 'hijo']],
  ['vivienda', ['vivienda', 'casa', 'domicilio', 'alquiler']],
  ['actividad e ingresos', ['trabajo', 'empleo', 'ingresos', 'rentas', 'sociedad', 'inversion']],
  ['documentación fiscal extranjera', ['certificado', 'declaracion', 'documentacion']],
];
const partialPatterns = [
  'han rechazado',
  'no haya considerado suficientes',
  'calcularon los dias',
  'pasaporte',
  'tarjetas de embarque',
  'billetes',
  'quien debe probar',
  'carga de probar',
  'carga al contribuyente',
  'carga de desmentir',
  'centro economico estaba fuera',
  'tarjetas y retiradas',
  'tarjetas y otros consumos',
  'requisitos se exigieron',
  'contenido debe tener un certificado',
  'vivienda permanente en ambos',
  'interactuan cdi',
  'convenio y',
  'diferencia los casos con sancion',
];
const askPatterns = [
  'se parece mas a mi',
  'parece mas a mi situacion',
  'dos paises me consideran',
  'espana y el otro estado dicen',
  'empleo extranjero e inversiones',
];
const domainTerms = [
  'residencia',
  'residente',
  'resido',
  'fiscal',
  'hacienda',
  'aeat',
  'tribunal',
  'prueba',
  'contribuyente',
  'irpf',
  'liquidacion',
  'sancion',
  'indicio',
  'sentencia',
  'caso',
  'fragmento',
  'pagina',
];

export const fold = (value: string) =>
  value.toLocaleLowerCase('es').normalize('NFKD').replace(/\p{M}/gu, '');
const matches = (text: string, needles: string[]) => needles.some((item) => text.includes(item));

export const analyzeQuery = (corpus: RetrievalCorpus, query: string): QueryAnalysis => {
  const text = fold(query);
  const criteria = facets.filter(([, words]) => matches(text, words)).map(([id]) => id);
  const evidenceCategories = evidence.filter(([, words]) => matches(text, words)).map(([id]) => id);
  const countries = [...new Set(corpus.units.flatMap((unit) => unit.facets.countries))]
    .sort()
    .filter((country) => text.includes(fold(country)));
  const years = [...new Set((text.match(/\b(?:19|20)\d{2}\b/g) ?? []).map(Number))];
  const personal =
    /\b(mi|mis|me|soy|estoy|estuve|vivo|resido|tengo|trabajo|gano|digo|aseguro)\b/.test(text);
  const missingFacts = factDimensions
    .filter(([, words]) => !matches(text, words))
    .map(([name]) => name);
  const covered = new Set(corpus.units.flatMap((unit) => unit.facets.criterion_ids));
  let uncoveredFacets = criteria.filter((criterion) => !covered.has(criterion));
  if (!criteria.length && !evidenceCategories.length && !matches(text, domainTerms)) {
    uncoveredFacets = ['OUT_OF_SCOPE'];
  }
  let behavior: QueryAnalysis['behavior'] = 'responder';
  let behaviorReasons = ['la consulta está cubierta por unidades y anclajes de la muestra'];
  if (uncoveredFacets.length) {
    behavior = 'abstenerse';
    behaviorReasons = ['la consulta pide una faceta sin cobertura estructurada en el corpus'];
  } else if (matches(text, askPatterns)) {
    behavior = 'preguntar';
    behaviorReasons = ['la comparación individual necesita hechos adicionales'];
  } else if (matches(text, partialPatterns)) {
    behavior = 'parcial';
    behaviorReasons = ['la muestra permite contexto, pero no una regla general completa'];
  } else if (
    personal &&
    missingFacts.length >= 4 &&
    !matches(text, ['automaticamente', 'por si solo', 'que sigue', 'rebatir', 'desvirtua'])
  ) {
    behavior = 'preguntar';
    behaviorReasons = ['el caso personal no contiene suficientes dimensiones comparables'];
  }
  return {
    criteria,
    evidenceCategories,
    countries,
    years,
    behavior,
    behaviorReasons,
    missingFacts,
    uncoveredFacets,
  };
};
