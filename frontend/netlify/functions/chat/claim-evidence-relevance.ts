import type { StrategySource } from './contracts';

const ignored = new Set([
  'administracion',
  'audiencia',
  'espana',
  'fiscal',
  'hecho',
  'judicial',
  'nacional',
  'resultado',
  'sala',
  'sentencia',
  'supremo',
  'tribunal',
  'valoracion',
]);

const terms = (value: string): Set<string> =>
  new Set(
    (
      value
        .toLocaleLowerCase('es')
        .normalize('NFKD')
        .replace(/\p{M}/gu, '')
        .match(/[a-z0-9]{4,}/g) ?? []
    ).filter((term) => !ignored.has(term))
  );

export const claimHasLexicalEvidence = (
  claim: string,
  sources: readonly StrategySource[]
): boolean => {
  const claimTerms = terms(claim);
  if (claimTerms.size < 2) return false;
  const evidenceTerms = terms(sources.map((source) => source.quote).join(' '));
  const overlap = [...claimTerms].filter((term) => evidenceTerms.has(term)).length;
  return overlap >= 2 && overlap / claimTerms.size >= 0.2;
};
