"""Construcción y clasificación de resultados de verificación de citas."""

from __future__ import annotations

from collections.abc import Sequence

from citation_models import (
    CitationVerification,
    EvidenceStatus,
    FragmentMatch,
    LiteralFidelity,
)


def build_verification_result(
    *,
    evidence_status: EvidenceStatus,
    declared_pdf_page_index: int | None,
    declared_page_valid: bool,
    matches: tuple[FragmentMatch, ...],
    has_ellipsis: bool,
) -> CitationVerification:
    """Construye el resultado y deriva su fidelidad literal."""

    matched = tuple(match for match in matches if match.matched)
    score = min((match.score for match in matches), default=0.0)
    return CitationVerification(
        evidence_status=evidence_status,
        literal_fidelity=_classify_literal_fidelity(
            evidence_status=evidence_status,
            matches=matches,
            has_ellipsis=has_ellipsis,
        ),
        score=round(score, 2),
        declared_pdf_page_index=declared_pdf_page_index,
        declared_page_valid=declared_page_valid,
        matched_pdf_page_indexes=tuple(
            sorted({match.pdf_page_index for match in matched if match.pdf_page_index is not None})
        ),
        matched_printed_page_labels=tuple(
            dict.fromkeys(match.printed_page_label for match in matched if match.printed_page_label)
        ),
        matched_fragment_count=len(matched),
        total_fragment_count=len(matches),
        fragment_matches=matches,
    )


def _classify_literal_fidelity(
    *,
    evidence_status: EvidenceStatus,
    matches: Sequence[FragmentMatch],
    has_ellipsis: bool,
) -> LiteralFidelity:
    if evidence_status is EvidenceStatus.PARTIAL_FRAGMENTS:
        return LiteralFidelity.PARTIAL
    if evidence_status in {EvidenceStatus.NOT_FOUND, EvidenceStatus.EXTRACTION_DEFECT}:
        return LiteralFidelity.UNVERIFIED
    if any(not match.exact for match in matches):
        return LiteralFidelity.FUZZY_CANDIDATE
    return LiteralFidelity.EXACT_WITH_ELLIPSIS if has_ellipsis else LiteralFidelity.EXACT
