/** Estado editorial calculado por Python y materializado desde el manifiesto. */
export type PublicationState = 'internal_preview' | 'publishable' | 'published';

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
