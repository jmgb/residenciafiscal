"""Verificación determinista de citas jurídicas contra texto extraído por páginas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from legal_text_matching import (
    normalize_legal_text,
    parse_page_number,
    score_fragment,
    split_citation_fragments,
)

DEFAULT_THRESHOLD = 85.0


class CitationStatus(StrEnum):
    """Resultado de buscar una cita siguiendo el orden de alcance acordado."""

    VERIFIED_DECLARED_PAGE = "verified_declared_page"
    VERIFIED_ADJACENT_PAGE = "verified_adjacent_page"
    VERIFIED_OTHER_PAGE = "verified_other_page"
    PARTIAL_FRAGMENTS = "partial_fragments"
    NOT_FOUND = "not_found"
    EXTRACTION_DEFECT = "extraction_defect"


@dataclass(frozen=True)
class FragmentMatch:
    """Mejor coincidencia encontrada para un fragmento de la cita."""

    fragment: str
    score: float
    page_number: int | None
    exact: bool
    matched: bool


@dataclass(frozen=True)
class CitationVerification:
    """Resultado completo y serializable de verificar una cita."""

    status: CitationStatus
    score: float
    declared_page: int | None
    declared_page_valid: bool
    matched_pages: tuple[int, ...]
    matched_fragment_count: int
    total_fragment_count: int
    fragment_matches: tuple[FragmentMatch, ...]


def _best_fragment_matches(
    fragments: Sequence[str],
    normalized_pages: Sequence[str],
    page_indexes: Sequence[int],
    threshold: float,
) -> tuple[FragmentMatch, ...]:
    matches: list[FragmentMatch] = []
    for fragment in fragments:
        best_score = 0.0
        best_page: int | None = None
        best_exact = False
        for page_index in page_indexes:
            score, exact = score_fragment(fragment, normalized_pages[page_index])
            if score <= best_score:
                continue
            best_score = score
            best_page = page_index + 1
            best_exact = exact
        matches.append(
            FragmentMatch(
                fragment=fragment,
                score=round(best_score, 2),
                page_number=best_page,
                exact=best_exact,
                matched=best_score >= threshold,
            )
        )
    return tuple(matches)


def _build_result(
    *,
    status: CitationStatus,
    declared_page: int | None,
    declared_page_valid: bool,
    matches: tuple[FragmentMatch, ...],
) -> CitationVerification:
    matched = tuple(match for match in matches if match.matched)
    score = min((match.score for match in matches), default=0.0)
    return CitationVerification(
        status=status,
        score=round(score, 2),
        declared_page=declared_page,
        declared_page_valid=declared_page_valid,
        matched_pages=tuple(
            sorted({match.page_number for match in matched if match.page_number is not None})
        ),
        matched_fragment_count=len(matched),
        total_fragment_count=len(matches),
        fragment_matches=matches,
    )


def verify_citation_pages(
    *,
    quote: str,
    declared_page: object,
    pages: Sequence[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> CitationVerification:
    """Busca una cita en página declarada, adyacentes y documento completo."""

    parsed_page = parse_page_number(declared_page)
    declared_page_valid = parsed_page is not None and parsed_page <= len(pages)
    normalized_pages = tuple(normalize_legal_text(page) for page in pages)
    fragments = split_citation_fragments(quote)

    if not fragments:
        return _build_result(
            status=CitationStatus.NOT_FOUND,
            declared_page=parsed_page,
            declared_page_valid=declared_page_valid,
            matches=(),
        )

    if not any(normalized_pages):
        return _build_result(
            status=CitationStatus.EXTRACTION_DEFECT,
            declared_page=parsed_page,
            declared_page_valid=declared_page_valid,
            matches=(),
        )

    declared_index = parsed_page - 1 if declared_page_valid and parsed_page is not None else None
    if declared_index is not None:
        declared_matches = _best_fragment_matches(
            fragments, normalized_pages, (declared_index,), threshold
        )
        if all(match.matched for match in declared_matches):
            return _build_result(
                status=CitationStatus.VERIFIED_DECLARED_PAGE,
                declared_page=parsed_page,
                declared_page_valid=True,
                matches=declared_matches,
            )

        nearby_indexes = tuple(
            index
            for index in (declared_index - 1, declared_index, declared_index + 1)
            if 0 <= index < len(pages)
        )
        nearby_matches = _best_fragment_matches(
            fragments, normalized_pages, nearby_indexes, threshold
        )
        if all(match.matched for match in nearby_matches):
            return _build_result(
                status=CitationStatus.VERIFIED_ADJACENT_PAGE,
                declared_page=parsed_page,
                declared_page_valid=True,
                matches=nearby_matches,
            )

    document_matches = _best_fragment_matches(
        fragments, normalized_pages, tuple(range(len(pages))), threshold
    )
    if all(match.matched for match in document_matches):
        return _build_result(
            status=CitationStatus.VERIFIED_OTHER_PAGE,
            declared_page=parsed_page,
            declared_page_valid=declared_page_valid,
            matches=document_matches,
        )

    status = (
        CitationStatus.PARTIAL_FRAGMENTS
        if any(match.matched for match in document_matches)
        else CitationStatus.NOT_FOUND
    )
    return _build_result(
        status=status,
        declared_page=parsed_page,
        declared_page_valid=declared_page_valid,
        matches=document_matches,
    )
