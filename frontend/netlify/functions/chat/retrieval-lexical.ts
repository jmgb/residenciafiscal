import { fold } from './retrieval-query-analysis';
import type { RetrievalCorpus, RetrievalUnit } from './retrieval-types';

const stopwords = new Set([
  'a',
  'al',
  'como',
  'con',
  'de',
  'del',
  'el',
  'en',
  'es',
  'la',
  'las',
  'lo',
  'los',
  'me',
  'mi',
  'para',
  'por',
  'que',
  'se',
  'si',
  'su',
  'un',
  'una',
  'y',
]);
const expansions: Record<string, string[]> = {
  hacienda: ['aeat', 'administracion'],
  demostrar: ['prueba', 'indicios', 'acreditar'],
  pruebas: ['prueba', 'evidencia', 'indicios'],
  dias: ['presencia', 'permanencia', 'desplazamientos'],
  familia: ['conyuge', 'hijos', 'familiar'],
  vivienda: ['domicilio', 'inmueble', 'ocupacion'],
  ingresos: ['rentas', 'economicos', 'actividad'],
  extranjero: ['exterior', 'fiscal', 'certificado'],
  certificado: ['documentacion', 'fiscal', 'extranjera'],
  sancion: ['culpabilidad', 'infraccion'],
};
const tokens = (text: string, expand: boolean): string[] => {
  const base = (fold(text).match(/[a-z0-9]+/g) ?? []).filter((token) => !stopwords.has(token));
  return expand ? [...base, ...base.flatMap((token) => expansions[token] ?? [])] : base;
};
const count = (values: string[]) => {
  const result = new Map<string, number>();
  for (const value of values) result.set(value, (result.get(value) ?? 0) + 1);
  return result;
};

export const rankUnits = (corpus: RetrievalCorpus, query: string) => {
  const documents = corpus.units.map((unit) => count(tokens(unit.search_text, false)));
  const frequencies = new Map<string, number>();
  for (const document of documents) {
    for (const token of document.keys()) frequencies.set(token, (frequencies.get(token) ?? 0) + 1);
  }
  const queryCounts = count(tokens(query, true));
  return corpus.units
    .map((unit, index) => {
      const lexical = [...queryCounts].reduce((total, [token, queryFrequency]) => {
        const inDocument = documents[index]?.get(token) ?? 0;
        return (
          total +
          Math.min(queryFrequency, inDocument) *
            (Math.log((documents.length + 1) / ((frequencies.get(token) ?? 0) + 1)) + 1)
        );
      }, 0);
      return { unit, lexical: Number(lexical.toFixed(8)) };
    })
    .sort(
      (left, right) =>
        right.lexical - left.lexical || left.unit.unit_id.localeCompare(right.unit.unit_id)
    );
};

export const caseSide = (unit: RetrievalUnit): string => {
  const residence = unit.facets.residence_determination?.spanish_residence;
  if (residence === 'RESIDENT_IN_SPAIN') return 'resident_spain';
  if (residence === 'NON_RESIDENT_IN_SPAIN' || residence === 'PARTIAL_YEAR_IN_SPAIN')
    return 'resident_abroad';
  if (unit.facets.issue_type === 'TAX_RESIDENCE') return 'mixed';
  if (unit.facets.outcome === 'GANA_AEAT') return 'aeat';
  if (unit.facets.outcome === 'GANA_CONTRIBUYENTE') return 'taxpayer';
  return 'mixed';
};
