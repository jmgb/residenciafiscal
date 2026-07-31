import type { StrategySource } from './contracts';

export interface VerbatimArtifact {
  source_sha256: string;
  pages: Array<{ page_index: number; raw_page_text: string }>;
}

export interface FileCitation {
  type?: string;
  page_number?: number;
  source?: string;
  custom_metadata?:
    | Record<string, unknown>
    | Array<{ key?: string; string_value?: string; numeric_value?: number }>;
}

const metadata = (citation: FileCitation): Record<string, unknown> => {
  if (!Array.isArray(citation.custom_metadata)) return citation.custom_metadata ?? {};
  return Object.fromEntries(
    citation.custom_metadata
      .filter((item) => item.key)
      .map((item) => [item.key as string, item.string_value ?? item.numeric_value])
  );
};

const normalizedWithMap = (value: string) => {
  const characters: string[] = [];
  const indexes: number[] = [];
  for (let index = 0; index < value.length; index += 1) {
    const folded = value[index]?.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase('es');
    for (const character of folded ?? '') {
      const next = /[a-z0-9]/.test(character) ? character : ' ';
      if (next === ' ' && characters.at(-1) === ' ') continue;
      characters.push(next);
      indexes.push(index);
    }
  }
  while (characters[0] === ' ') {
    characters.shift();
    indexes.shift();
  }
  while (characters.at(-1) === ' ') {
    characters.pop();
    indexes.pop();
  }
  return { normalized: characters.join(''), indexes };
};

const extractQuote = (candidate: string, pageText: string): string | null => {
  if (pageText.includes(candidate)) return candidate;
  const page = normalizedWithMap(pageText);
  const wanted = normalizedWithMap(candidate).normalized;
  const start = page.normalized.indexOf(wanted);
  if (start < 0 || !wanted) return null;
  const sourceStart = page.indexes[start];
  const sourceEnd = page.indexes[start + wanted.length - 1];
  if (sourceStart === undefined || sourceEnd === undefined) return null;
  return pageText.slice(sourceStart, sourceEnd + 1);
};

export const verifyFileCitation = (
  citation: FileCitation,
  artifacts: Record<string, VerbatimArtifact>
): StrategySource | null => {
  const values = metadata(citation);
  const judgmentId = values.judgment_id;
  const sourceSha256 = values.source_sha256;
  if (typeof judgmentId !== 'string' || typeof sourceSha256 !== 'string') return null;
  const artifact = artifacts[judgmentId];
  if (!artifact || artifact.source_sha256 !== sourceSha256) return null;
  if (typeof citation.page_number !== 'number' || typeof citation.source !== 'string') return null;
  const page = artifact.pages.find((item) => item.page_index === citation.page_number);
  if (!page) return null;
  const quote = extractQuote(citation.source.trim(), page.raw_page_text);
  if (!quote) return null;
  return {
    strategy: 'gemini_file_search',
    judgment_id: judgmentId,
    page: citation.page_number,
    source_sha256: sourceSha256,
    quote,
    verification: 'EXACT',
  };
};
