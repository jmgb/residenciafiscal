import type { StrategySource } from './contracts';
import type { ChatRetrievalResult } from './structured-retrieval';

interface Fragment {
  page_index: number;
  printed_page?: string | null;
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

export interface EvidenceBundle {
  contextJson: string;
  sourcesByEvidenceId: Map<string, StrategySource>;
}

const MAX_CONTEXT_BYTES = 43 * 1024;
const MAX_JUDGMENT_BYTES = 4 * 1024;

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

const selectFragments = (unit: EvidenceUnit, queryTerms: Set<string>) =>
  unit.source_anchors
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
    .sort((left, right) => right.score - left.score || left.order - right.order)
    .slice(0, 2);

const byteLength = (value: unknown) => new TextEncoder().encode(JSON.stringify(value)).byteLength;

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
  query: string
): EvidenceBundle => {
  const corpus = rawCorpus as EvidenceCorpus;
  const unitsById = new Map(corpus.units.map((unit) => [unit.unit_id, unit]));
  const contextUnits: unknown[] = [];
  const evidence: unknown[] = [];
  const sourcesByEvidenceId = new Map<string, StrategySource>();
  const queryTerms = terms(query);
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
    for (const { anchor, fragment } of selectFragments(unit, queryTerms)) {
      const evidenceId = `E${evidenceNumber}`;
      const evidenceItem = {
        evidence_id: evidenceId,
        unit_id: unit.unit_id,
        judgment_id: unit.judgment_id,
        role: hit.role,
        anchor_id: anchor.anchor_id,
        purpose: anchor.purpose,
        page: fragment.page_index,
        printed_page: fragment.printed_page ?? null,
        quote: fragment.verbatim_text,
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
        quote: fragment.verbatim_text,
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
    if (byteLength(prospective) > MAX_CONTEXT_BYTES) break;
    contextUnits.push(packedUnit);
    evidence.push(...hitEvidence);
    for (const [evidenceId, source] of hitSources) sourcesByEvidenceId.set(evidenceId, source);
  }
  return {
    contextJson: JSON.stringify({ units: contextUnits, evidence }),
    sourcesByEvidenceId,
  };
};
