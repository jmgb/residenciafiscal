import type {
  ChatSourceV2,
  LegacyChatSource,
  LegalReviewStatus,
  TechnicalReviewStatus,
} from '@/types/chat';

const VALID_RESULTS = new Set([
  'GANA_AEAT',
  'GANA_CONTRIBUYENTE',
  'PARCIAL',
  'RETROACCION',
  'INADMISION',
  'DESCONOCIDO',
]);

const TECHNICAL_REVIEW_STATUSES = new Set<TechnicalReviewStatus>([
  'GENERATED',
  'VALIDATED',
  'NEEDS_REVIEW',
  'REJECTED',
]);

const LEGAL_REVIEW_STATUSES = new Set<LegalReviewStatus>([
  'UNREVIEWED',
  'AGENT_REVIEWED',
  'HUMAN_APPROVED',
  'REJECTED',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function hasCorpusEntryShape(value: Record<string, unknown>): boolean {
  return (
    typeof value.archivo === 'string' &&
    typeof value.roj === 'string' &&
    typeof value.ecli === 'string' &&
    typeof value.organo === 'string' &&
    typeof value.fecha === 'string' &&
    typeof value.resultado === 'string' &&
    VALID_RESULTS.has(value.resultado) &&
    Array.isArray(value.criterioDecisivo) &&
    value.criterioDecisivo.every((criterio) => typeof criterio === 'string') &&
    typeof value.esCasoResidencia === 'boolean'
  );
}

export function isChatSourceV2(value: unknown): value is ChatSourceV2 {
  if (!isRecord(value) || !hasCorpusEntryShape(value) || !isRecord(value.reviewStatus)) {
    return false;
  }

  return (
    isNonEmptyString(value.sourceId) &&
    isNonEmptyString(value.issueId) &&
    isNonEmptyString(value.issueLabel) &&
    isNonEmptyString(value.anchorId) &&
    Number.isInteger(value.pageIndex) &&
    Number(value.pageIndex) > 0 &&
    (value.printedPage === null || isNonEmptyString(value.printedPage)) &&
    isNonEmptyString(value.extracto) &&
    (value.fidelity === 'exact' || value.fidelity === 'exact_with_ellipsis') &&
    typeof value.sourceSha256 === 'string' &&
    /^[0-9a-f]{64}$/.test(value.sourceSha256) &&
    typeof value.reviewStatus.technical === 'string' &&
    TECHNICAL_REVIEW_STATUSES.has(value.reviewStatus.technical as TechnicalReviewStatus) &&
    typeof value.reviewStatus.legal === 'string' &&
    LEGAL_REVIEW_STATUSES.has(value.reviewStatus.legal as LegalReviewStatus)
  );
}

export function isLegacyChatSource(value: unknown): value is LegacyChatSource {
  return (
    isRecord(value) &&
    !('sourceId' in value) &&
    hasCorpusEntryShape(value) &&
    typeof value.extracto === 'string'
  );
}

export function areChatSourcesV2(value: unknown): value is ChatSourceV2[] {
  if (!Array.isArray(value) || !value.every(isChatSourceV2)) return false;
  return new Set(value.map((source) => source.sourceId)).size === value.length;
}
