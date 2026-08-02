export type JudicialAuthorityIntent = 'tribunal_supremo' | 'audiencia_nacional';
export type JudicialAuthorityMatch = 'direct' | 'missing' | 'not_requested';

const fold = (value: string) =>
  value.toLocaleLowerCase('es').normalize('NFKD').replace(/\p{M}/gu, '');

export const requestedJudicialAuthority = (query: string): JudicialAuthorityIntent | null => {
  const text = fold(query);
  const supreme = /\b(tribunal supremo|supremo|sts)\b/.test(text);
  const nationalCourt = /\b(audiencia nacional|san)\b/.test(text);
  if (supreme === nationalCourt) return null;
  return supreme ? 'tribunal_supremo' : 'audiencia_nacional';
};

export const judgmentAuthority = (judgmentId: string): JudicialAuthorityIntent | 'other' => {
  const normalized = judgmentId.toLocaleLowerCase('es');
  if (normalized.startsWith('sts-')) return 'tribunal_supremo';
  if (normalized.startsWith('san-')) return 'audiencia_nacional';
  return 'other';
};

export const authorityMetadataFilter = (intent: JudicialAuthorityIntent | null): string | null => {
  if (intent === 'tribunal_supremo') return 'authority="tribunal_supremo"';
  if (intent === 'audiencia_nacional') return 'authority="audiencia_nacional"';
  return null;
};

export const localAuthorityFilter = (intent: JudicialAuthorityIntent | null): string | null =>
  intent ? `local_authority="${intent}"` : null;

export const authorityMatch = (
  intent: JudicialAuthorityIntent | null,
  judgmentIds: readonly string[]
): JudicialAuthorityMatch => {
  if (!intent) return 'not_requested';
  return judgmentIds.some((id) => judgmentAuthority(id) === intent) ? 'direct' : 'missing';
};

export const authorityLabel = (intent: JudicialAuthorityIntent): string =>
  intent === 'tribunal_supremo' ? 'Tribunal Supremo' : 'Audiencia Nacional';
