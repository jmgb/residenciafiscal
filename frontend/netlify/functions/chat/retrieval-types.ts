export type Behavior = 'responder' | 'parcial' | 'preguntar' | 'abstenerse';

export interface RetrievalUnit {
  unit_id: string;
  judgment_id: string;
  search_text: string;
  facets: {
    criterion_ids: string[];
    evidence_categories: string[];
    countries: string[];
    tax_years: number[];
    outcome: string;
    issue_type: string;
    residence_determination?: { spanish_residence: string } | null;
  };
  evidence_findings: unknown[];
  presence_events: unknown[];
  presence_periods: unknown[];
  source_anchors: unknown[];
}

export interface RetrievalCorpus {
  units: RetrievalUnit[];
}

export interface QueryAnalysis {
  criteria: string[];
  evidenceCategories: string[];
  countries: string[];
  years: number[];
  behavior: Behavior;
  behaviorReasons: string[];
  missingFacts: string[];
  uncoveredFacets: string[];
}
