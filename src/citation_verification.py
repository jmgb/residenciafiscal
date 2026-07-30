"""Verificación determinista de citas jurídicas contra texto extraído por páginas."""

from __future__ import annotations

from collections.abc import Sequence

from citation_models import (
    CitationVerification,
    EvidenceStatus,
    ExtractedPage,
    FragmentMatch,
    LiteralFidelity,
)
from citation_result_builder import build_verification_result
from legal_text_matching import (
    extract_verbatim_fragment,
    normalize_legal_text,
    parse_page_number,
    score_fragment,
    split_citation_fragments,
)

DEFAULT_THRESHOLD = 85.0

__all__ = [
    "DEFAULT_THRESHOLD",
    "EvidenceStatus",
    "ExtractedPage",
    "LiteralFidelity",
    "normalize_legal_text",
    "parse_page_number",
    "split_citation_fragments",
    "verify_citation_pages",
]


def _best_fragment_matches(
    fragments: Sequence[str],
    pages: Sequence[ExtractedPage],
    normalized_pages: Sequence[str],
    page_positions: Sequence[int],
    threshold: float,
) -> tuple[FragmentMatch, ...]:
    matches: list[FragmentMatch] = []
    for fragment in fragments:
        best_score = 0.0
        best_page: ExtractedPage | None = None
        best_exact = False
        for page_position in page_positions:
            score, exact = score_fragment(fragment, normalized_pages[page_position])
            if score <= best_score:
                continue
            best_score = score
            best_page = pages[page_position]
            best_exact = exact
        matches.append(
            FragmentMatch(
                fragment=fragment,
                score=round(best_score, 2),
                pdf_page_index=best_page.pdf_page_index if best_page else None,
                printed_page_label=best_page.printed_page_label if best_page else None,
                exact=best_exact,
                matched=best_score >= threshold,
                source_excerpt_verbatim=(
                    extract_verbatim_fragment(fragment, best_page.text)
                    if best_exact and best_page
                    else None
                ),
            )
        )
    return tuple(matches)


def _coerce_pages(pages: Sequence[str | ExtractedPage]) -> tuple[ExtractedPage, ...]:
    return tuple(
        page
        if isinstance(page, ExtractedPage)
        else ExtractedPage(pdf_page_index=index, printed_page_label=None, text=page)
        for index, page in enumerate(pages, 1)
    )


def verify_citation_pages(
    *,
    quote: str,
    declared_page: object,
    pages: Sequence[str | ExtractedPage],
    threshold: float = DEFAULT_THRESHOLD,
) -> CitationVerification:
    """Busca una cita en página declarada, adyacentes y documento completo."""

    extracted_pages = _coerce_pages(pages)
    parsed_page = parse_page_number(declared_page)
    page_position_by_pdf_index = {
        page.pdf_page_index: position for position, page in enumerate(extracted_pages)
    }
    declared_page_valid = parsed_page in page_position_by_pdf_index
    normalized_pages = tuple(normalize_legal_text(page.text) for page in extracted_pages)
    fragments = split_citation_fragments(quote)
    has_ellipsis = len(fragments) > 1

    if not fragments:
        return build_verification_result(
            evidence_status=EvidenceStatus.NOT_FOUND,
            declared_pdf_page_index=parsed_page,
            declared_page_valid=declared_page_valid,
            matches=(),
            has_ellipsis=False,
        )

    if not any(normalized_pages):
        return build_verification_result(
            evidence_status=EvidenceStatus.EXTRACTION_DEFECT,
            declared_pdf_page_index=parsed_page,
            declared_page_valid=declared_page_valid,
            matches=(),
            has_ellipsis=has_ellipsis,
        )

    declared_position = (
        page_position_by_pdf_index.get(parsed_page) if parsed_page is not None else None
    )
    if declared_position is not None:
        declared_matches = _best_fragment_matches(
            fragments, extracted_pages, normalized_pages, (declared_position,), threshold
        )
        if all(match.matched for match in declared_matches):
            return build_verification_result(
                evidence_status=EvidenceStatus.FOUND_DECLARED_PAGE,
                declared_pdf_page_index=parsed_page,
                declared_page_valid=True,
                matches=declared_matches,
                has_ellipsis=has_ellipsis,
            )

        nearby_positions = tuple(
            position
            for position in (
                declared_position - 1,
                declared_position,
                declared_position + 1,
            )
            if 0 <= position < len(extracted_pages)
        )
        nearby_matches = _best_fragment_matches(
            fragments, extracted_pages, normalized_pages, nearby_positions, threshold
        )
        if all(match.matched for match in nearby_matches):
            return build_verification_result(
                evidence_status=EvidenceStatus.FOUND_ADJACENT_PAGE,
                declared_pdf_page_index=parsed_page,
                declared_page_valid=True,
                matches=nearby_matches,
                has_ellipsis=has_ellipsis,
            )

    document_matches = _best_fragment_matches(
        fragments,
        extracted_pages,
        normalized_pages,
        tuple(range(len(extracted_pages))),
        threshold,
    )
    if all(match.matched for match in document_matches):
        return build_verification_result(
            evidence_status=EvidenceStatus.FOUND_OTHER_PAGE,
            declared_pdf_page_index=parsed_page,
            declared_page_valid=declared_page_valid,
            matches=document_matches,
            has_ellipsis=has_ellipsis,
        )

    evidence_status = (
        EvidenceStatus.PARTIAL_FRAGMENTS
        if any(match.matched for match in document_matches)
        else EvidenceStatus.NOT_FOUND
    )
    return build_verification_result(
        evidence_status=evidence_status,
        declared_pdf_page_index=parsed_page,
        declared_page_valid=declared_page_valid,
        matches=document_matches,
        has_ellipsis=has_ellipsis,
    )
