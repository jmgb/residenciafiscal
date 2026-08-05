import type { StrategySource } from './contracts';
import type { ChatRetrievalResult } from './structured-retrieval';

interface Fragment {
  page_index: number;
  printed_page?: string | null;
  start_offset?: number;
  end_offset?: number;
  verbatim_text: string;
}

interface Anchor {
  anchor_id: string;
  purpose: string;
  source_sha256: string;
  fragments: Fragment[];
}

interface EvidenceUnit {
  unit_id: string;
  judgment_id: string;
  issue: unknown;
  holding: unknown;
  facts: unknown[];
  evidence_findings: unknown[];
  legal_rules: unknown[];
  burden_of_proof_steps: unknown[];
  presence_periods: unknown[];
  treaty_analyses: unknown[];
  source_anchors: Anchor[];
}

interface EvidenceCorpus {
  units: EvidenceUnit[];
}

interface VerbatimArtifact {
  source_sha256: string;
  pages: Array<{ page_index: number; raw_page_text: string }>;
}

export interface EvidenceBundle {
  contextJson: string;
  sourcesByEvidenceId: Map<string, StrategySource>;
  purposesByEvidenceId: Map<string, string>;
}

export const MAX_CONTEXT_BYTES = 43 * 1024;
const MAX_JUDGMENT_BYTES = 4 * 1024;
const MAX_FRAGMENTS_PER_JUDGMENT = 4;

const purposeWeight: Record<string, number> = {
  HOLDING: 6,
  REASONING: 5,
  EVIDENCE: 4,
  BURDEN_OF_PROOF: 4,
  TREATY: 4,
  LEGAL_RULE: 3,
  FACT: 2,
};
const stopwords = new Set([
  'como',
  'cual',
  'cuando',
  'donde',
  'espana',
  'fiscal',
  'hacienda',
  'para',
  'porque',
  'que',
  'residencia',
  'tiene',
  'una',
]);

const terms = (text: string) =>
  new Set(
    (
      text
        .toLocaleLowerCase('es')
        .normalize('NFD')
        .replace(/\p{M}/gu, '')
        .match(/[a-z0-9]{3,}/g) ?? []
    ).filter((token) => !stopwords.has(token))
  );

const queryTerms = (query: string) => {
  const result = terms(query);
  if (/\b(?:gym|gimnasio|gimnasios)\b/i.test(query)) {
    for (const term of ['gimnasio', 'gimnasios', 'cuota', 'cuotas', 'clubs', 'deportivos']) {
      result.add(term);
    }
  }
  return result;
};

const selectFragments = (unit: EvidenceUnit, queryTerms: Set<string>) => {
  const ranked = unit.source_anchors
    .flatMap((anchor, anchorIndex) =>
      anchor.fragments.map((fragment, fragmentIndex) => {
        const overlap = [...terms(fragment.verbatim_text)].filter((token) =>
          queryTerms.has(token)
        ).length;
        return {
          anchor,
          fragment,
          score: overlap * 10 + (purposeWeight[anchor.purpose] ?? 0),
          order: anchorIndex * 1000 + fragmentIndex,
        };
      })
    )
    .sort((left, right) => right.score - left.score || left.order - right.order);
  const selected = ranked.slice(0, 1);
  for (const purpose of ['HOLDING', 'REASONING', 'BURDEN_OF_PROOF']) {
    if (selected.some((item) => item.anchor.purpose === purpose)) continue;
    const candidate = ranked.find(
      (item) => item.anchor.purpose === purpose && !selected.includes(item)
    );
    if (candidate) selected.push(candidate);
    if (selected.length === MAX_FRAGMENTS_PER_JUDGMENT) return selected;
  }
  for (const candidate of ranked) {
    if (!selected.includes(candidate)) selected.push(candidate);
    if (selected.length === MAX_FRAGMENTS_PER_JUDGMENT) break;
  }
  return selected;
};

const byteLength = (value: unknown) => new TextEncoder().encode(JSON.stringify(value)).byteLength;

const expandedQuote = (
  judgmentId: string,
  anchor: Anchor,
  fragment: Fragment,
  artifacts?: Record<string, VerbatimArtifact>
): string => {
  const artifact = artifacts?.[judgmentId];
  if (!artifact || artifact.source_sha256 !== anchor.source_sha256) return fragment.verbatim_text;
  if (!Number.isInteger(fragment.start_offset) || !Number.isInteger(fragment.end_offset)) {
    return fragment.verbatim_text;
  }
  const page = artifact.pages.find((candidate) => candidate.page_index === fragment.page_index);
  if (!page) return fragment.verbatim_text;
  const rawStart = Math.max(0, (fragment.start_offset as number) - 240);
  const rawEnd = Math.min(page.raw_page_text.length, (fragment.end_offset as number) + 360);
  const firstWhitespace = page.raw_page_text.indexOf(' ', rawStart);
  const lastWhitespace = page.raw_page_text.lastIndexOf(' ', rawEnd);
  const start =
    firstWhitespace >= 0 && firstWhitespace < (fragment.start_offset as number)
      ? firstWhitespace + 1
      : rawStart;
  const end = lastWhitespace > (fragment.end_offset as number) ? lastWhitespace : rawEnd;
  const quote = page.raw_page_text.slice(start, end).trim();
  return quote.includes(fragment.verbatim_text) ? quote : fragment.verbatim_text;
};

const packUnit = (
  unit: EvidenceUnit,
  role: string,
  selectedEvidence: unknown[]
): Record<string, unknown> => {
  const packed: Record<string, unknown> = {
    unit_id: unit.unit_id,
    judgment_id: unit.judgment_id,
    role,
  };
  const fits = (candidate: Record<string, unknown>) =>
    byteLength({ unit: candidate, evidence: selectedEvidence }) <= MAX_JUDGMENT_BYTES;
  const addValue = (key: string, value: unknown) => {
    const candidate = { ...packed, [key]: value };
    if (fits(candidate)) Object.assign(packed, { [key]: value });
  };
  addValue('issue', unit.issue);
  addValue('holding', unit.holding);
  const sections: Array<[string, unknown[]]> = [
    ['evidence_findings', unit.evidence_findings],
    ['facts', unit.facts],
    ['legal_rules', unit.legal_rules],
    ['burden_of_proof', unit.burden_of_proof_steps],
    ['presence_periods', unit.presence_periods],
    ['treaty_analyses', unit.treaty_analyses],
  ];
  for (const [key, values] of sections) {
    const packedValues: unknown[] = [];
    for (const value of values) {
      const candidate = { ...packed, [key]: [...packedValues, value] };
      if (!fits(candidate)) break;
      packedValues.push(value);
    }
    if (packedValues.length) Object.assign(packed, { [key]: packedValues });
  }
  return packed;
};

export const buildEvidenceBundle = (
  rawCorpus: unknown,
  retrieval: ChatRetrievalResult,
  query: string,
  artifacts?: Record<string, VerbatimArtifact>,
  // El contexto conversacional comparte prompt con la evidencia. Se descuenta aquí
  // en vez de bajar el presupuesto fijo, para que un primer turno —sin historial—
  // siga recibiendo exactamente la misma evidencia que antes.
  maxContextBytes = MAX_CONTEXT_BYTES
): EvidenceBundle => {
  const corpus = rawCorpus as EvidenceCorpus;
  const unitsById = new Map(corpus.units.map((unit) => [unit.unit_id, unit]));
  const contextUnits: unknown[] = [];
  const evidence: unknown[] = [];
  const sourcesByEvidenceId = new Map<string, StrategySource>();
  const purposesByEvidenceId = new Map<string, string>();
  const selectedQueryTerms = queryTerms(query);
  let evidenceNumber = 1;

  for (const hit of retrieval.hits) {
    const unit = unitsById.get(hit.unitId);
    if (!unit) throw new Error(`Unidad recuperada ausente: ${hit.unitId}`);
    const hitEvidence: unknown[] = [];
    const hitSources = new Map<string, StrategySource>();
    const minimalUnit = {
      unit_id: unit.unit_id,
      judgment_id: unit.judgment_id,
      role: hit.role,
    };
    for (const { anchor, fragment } of selectFragments(unit, selectedQueryTerms)) {
      const evidenceId = `E${evidenceNumber}`;
      const quote = expandedQuote(unit.judgment_id, anchor, fragment, artifacts);
      const evidenceItem = {
        evidence_id: evidenceId,
        unit_id: unit.unit_id,
        judgment_id: unit.judgment_id,
        role: hit.role,
        anchor_id: anchor.anchor_id,
        purpose: anchor.purpose,
        page: fragment.page_index,
        printed_page: fragment.printed_page ?? null,
        quote,
      };
      const prospectiveEvidence = [...hitEvidence, evidenceItem];
      if (byteLength({ unit: minimalUnit, evidence: prospectiveEvidence }) > MAX_JUDGMENT_BYTES)
        break;
      hitEvidence.push(evidenceItem);
      hitSources.set(evidenceId, {
        strategy: 'current_structured',
        judgment_id: unit.judgment_id,
        page: fragment.page_index,
        source_sha256: anchor.source_sha256,
        quote,
        verification: 'EXACT',
      });
      evidenceNumber += 1;
    }
    if (!hitEvidence.length) continue;
    const packedUnit = packUnit(unit, hit.role, hitEvidence);
    const prospective = {
      units: [...contextUnits, packedUnit],
      evidence: [...evidence, ...hitEvidence],
    };
    if (byteLength(prospective) > maxContextBytes) break;
    contextUnits.push(packedUnit);
    evidence.push(...hitEvidence);
    for (const [evidenceId, source] of hitSources) sourcesByEvidenceId.set(evidenceId, source);
    for (const item of hitEvidence) {
      const typed = item as { evidence_id: string; purpose: string };
      purposesByEvidenceId.set(typed.evidence_id, typed.purpose);
    }
  }
  return {
    contextJson: JSON.stringify({ units: contextUnits, evidence }),
    sourcesByEvidenceId,
    purposesByEvidenceId,
  };
};
