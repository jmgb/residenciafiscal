import { judgmentAuthority, requestedJudicialAuthority } from './judicial-authority';
import { caseSide, rankUnits } from './retrieval-lexical';
import { analyzeQuery } from './retrieval-query-analysis';
import type { Behavior, RetrievalCorpus } from './retrieval-types';

export interface StructuredHit {
  unitId: string;
  judgmentId: string;
  role: 'support' | 'contrast';
  sourceAnchors: unknown[];
}

export interface ChatRetrievalResult {
  behavior: Behavior;
  behaviorReasons: string[];
  missingFacts: string[];
  uncoveredFacets: string[];
  hits: StructuredHit[];
}

export const retrieveForChat = (
  rawCorpus: unknown,
  query: string,
  limit = 5
): ChatRetrievalResult => {
  if (limit < 1) throw new Error('limit debe ser positivo');
  const corpus = rawCorpus as RetrievalCorpus;
  const analysis = analyzeQuery(corpus, query);
  if (analysis.behavior === 'preguntar' || analysis.behavior === 'abstenerse') {
    return {
      behavior: analysis.behavior,
      behaviorReasons: analysis.behaviorReasons,
      missingFacts: analysis.missingFacts,
      uncoveredFacets: analysis.uncoveredFacets,
      hits: [],
    };
  }

  const ranked = rankUnits(corpus, query).map(({ unit, lexical }) => {
    const criterionBoost =
      2 * unit.facets.criterion_ids.filter((id) => analysis.criteria.includes(id)).length;
    const evidenceBoost =
      1.25 *
      unit.facets.evidence_categories.filter((id) => analysis.evidenceCategories.includes(id))
        .length;
    const countryBoost =
      1.5 * unit.facets.countries.filter((country) => analysis.countries.includes(country)).length;
    let periodBoost = unit.facets.tax_years.filter((year) => analysis.years.includes(year)).length;
    if (analysis.criteria.includes('CRIT_183_DIAS')) {
      periodBoost += 2 * unit.presence_events.length + unit.presence_periods.length;
    }
    return {
      unit,
      total: Number(
        (lexical + criterionBoost + evidenceBoost + countryBoost + periodBoost).toFixed(8)
      ),
    };
  });
  ranked.sort(
    (left, right) =>
      right.total - left.total ||
      right.unit.evidence_findings.length - left.unit.evidence_findings.length ||
      left.unit.unit_id.localeCompare(right.unit.unit_id)
  );
  const authorityIntent = requestedJudicialAuthority(query);
  const authorityRanked = authorityIntent
    ? ranked.filter((item) => judgmentAuthority(item.unit.judgment_id) === authorityIntent)
    : ranked;
  const scopedRanked = authorityRanked.length ? authorityRanked : ranked;
  const bestByJudgment = new Map<string, (typeof ranked)[number]>();
  for (const item of scopedRanked) {
    if (!bestByJudgment.has(item.unit.judgment_id)) {
      bestByJudgment.set(item.unit.judgment_id, item);
    }
  }
  const candidates = [...bestByJudgment.values()];
  const selected = candidates.splice(0, 1);
  const firstSide = selected[0] ? caseSide(selected[0].unit) : 'mixed';
  const contrastIndex = candidates.findIndex((item) => caseSide(item.unit) !== firstSide);
  if (contrastIndex >= 0 && limit > 1) selected.push(...candidates.splice(contrastIndex, 1));
  selected.push(...candidates.slice(0, Math.max(0, limit - selected.length)));

  return {
    behavior: analysis.behavior,
    behaviorReasons: analysis.behaviorReasons,
    missingFacts: analysis.missingFacts,
    uncoveredFacets: analysis.uncoveredFacets,
    hits: selected.slice(0, limit).map(({ unit }, index) => ({
      unitId: unit.unit_id,
      judgmentId: unit.judgment_id,
      role: index > 0 && caseSide(unit) !== firstSide ? 'contrast' : 'support',
      sourceAnchors: unit.source_anchors,
    })),
  };
};
