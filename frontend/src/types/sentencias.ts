/**
 * Proyección pública de una sentencia, tal como la sirve
 * `scripts/build-sentencias.mjs` desde `knowledge/jurisprudencia-v3/publico/`.
 *
 * Es una **allowlist** producida por `src/public_judgment_projection.py`: el
 * frontend nunca recibe el caso canónico. Añadir un campo aquí no lo publica;
 * hay que añadirlo antes en la proyección de Python, que es donde la decisión
 * queda registrada.
 */

/** `internal_preview` nunca es indexable, pase lo que pase en el frontend. */
export type PublicationState = 'internal_preview' | 'publishable' | 'published';

export interface RevisionEstado {
  legal: string;
  technical: string;
  reviewedAt?: string | null;
  reviewedBy?: string | null;
}

export interface SentenciaIndexEntry {
  judgmentId: string;
  roj: string;
  court: string;
  decisionDate: string;
  taxYears: number[];
  criterionIds: string[];
  outcomes: string[];
  jurisdictions: string[];
  publicationState: PublicationState;
  legalReview: string;
}

export interface SentenciasIndex {
  schemaVersion: string;
  jurisdiction: string;
  /** Candidatas del corpus, publicadas o no. Distingue «vacío» de «roto». */
  candidates: number;
  includesPreview: boolean;
  judgments: SentenciaIndexEntry[];
}

export interface FragmentoLiteral {
  pageIndex: number;
  printedPage: string | null;
  /** Subcadena exacta del PDF. No se recorta, une ni reformatea en ninguna capa. */
  verbatimText: string;
}

export interface AnclajeLiteral {
  anchorId: string;
  purpose: string;
  fidelity: string;
  sourceSha256: string;
  fragments: FragmentoLiteral[];
  review: RevisionEstado;
}

export interface DeterminacionResidencial {
  spanishResidence: string;
  otherCountry?: string | null;
  nonResidentFrom?: string | null;
  taxYears: number[];
}

export interface FalloCuestion {
  holdingId: string;
  outcome: string;
  conclusion: string;
  decisiveReasoning?: string | null;
  consequences: string[];
  residenceDetermination?: DeterminacionResidencial | null;
  anchorIds: string[];
  review: RevisionEstado;
}

export interface PruebaValorada {
  evidenceId: string;
  category: string;
  subtype?: string | null;
  description: string;
  offeredBy: string;
  assessment: string;
  assessmentReason?: string | null;
  role?: string | null;
  probativePurpose?: string | null;
  anchorIds: string[];
  review: RevisionEstado;
}

export interface HechoProbado {
  factId: string;
  category: string;
  description: string;
  country?: string | null;
  place?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  taxYears: number[];
  proceduralStatus?: string | null;
  anchorIds: string[];
  review: RevisionEstado;
}

export interface NormaAplicada {
  legalRuleId: string;
  ruleType: string;
  citation: string;
  proposition: string;
  anchorIds: string[];
  review: RevisionEstado;
}

export interface PasoCarga {
  stepId: string;
  sequence: number;
  initialBearer: string;
  factToProve: string;
  responseRequired?: string | null;
  shiftsTo?: string | null;
  conclusion?: string | null;
  anchorIds: string[];
  review: RevisionEstado;
}

export interface PeriodoPresencia {
  periodId: string;
  country?: string | null;
  classification: string;
  startDate?: string | null;
  endDate?: string | null;
  dayCount?: number | null;
  countedFor183DayRule?: boolean | null;
  calculationMethod?: string | null;
  anchorIds: string[];
  review: RevisionEstado;
}

export interface AnalisisConvenio {
  treatyAnalysisId: string;
  treatyCitation: string;
  countries: string[];
  dualResidenceEstablished?: boolean | null;
  resultCountry?: string | null;
  anchorIds: string[];
  review: RevisionEstado;
}

export interface CuestionJuridica {
  issueId: string;
  issueType: string;
  question: string;
  criterionIds: string[];
  holding?: FalloCuestion | null;
  facts: HechoProbado[];
  evidence: PruebaValorada[];
  legalRules: NormaAplicada[];
  burdenOfProof: PasoCarga[];
  presencePeriods: PeriodoPresencia[];
  treatyAnalyses: AnalisisConvenio[];
  anchorIds: string[];
  review: RevisionEstado;
}

export interface IdentidadSentencia {
  judgmentId: string;
  roj: string;
  ecli: string;
  court: string;
  chamber?: string | null;
  decisionDate: string;
  taxYears: number[];
  pageCount: number;
  sourceFile: string;
  sourceSha256: string;
  isTaxResidenceCase: boolean;
  provenance: { producer: string; modelId: string; generatedAt: string };
  review: RevisionEstado;
}

export interface JurisdiccionSentencia {
  code: string;
  /** Solo roles que autorizan enlace: `mentioned_only` no llega hasta aquí. */
  roles: string[];
  treatyBoeId?: string | null;
}

export interface SentenciaPublica {
  schemaVersion: string;
  jurisdiction: string;
  publicationState: PublicationState;
  judgment: IdentidadSentencia;
  issues: CuestionJuridica[];
  anchors: AnclajeLiteral[];
  jurisdictions: JurisdiccionSentencia[];
}
