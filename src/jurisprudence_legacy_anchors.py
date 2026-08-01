"""Localización literal de citas legadas sobre el corpus verbatim."""

from __future__ import annotations

from dataclasses import dataclass

from legal_text_matching import (
    normalize_legal_text_with_spans,
    parse_page_number,
    split_citation_fragments,
)
from verbatim_models import VerbatimCorpus, VerbatimPage


@dataclass(frozen=True)
class LocatedFragment:
    page_index: int
    start_offset: int
    end_offset: int
    verbatim_text: str


def _page_order(verbatim: VerbatimCorpus, declared_page: object) -> tuple[VerbatimPage, ...]:
    declared = parse_page_number(declared_page)
    priority = (declared, declared - 1 if declared else None, declared + 1 if declared else None)
    indexes = tuple(item for item in priority if item and 1 <= item <= verbatim.page_count)
    ordered = tuple(dict.fromkeys((*indexes, *(page.page_index for page in verbatim.pages))))
    pages = {page.page_index: page for page in verbatim.pages}
    return tuple(pages[index] for index in ordered)


def _locate_fragment(fragment: str, pages: tuple[VerbatimPage, ...]) -> LocatedFragment | None:
    for page in pages:
        normalized, spans = normalize_legal_text_with_spans(page.raw_page_text)
        start = normalized.find(fragment)
        if start < 0:
            continue
        end = start + len(fragment)
        source_start = spans[start][0]
        source_end = spans[end - 1][1]
        verbatim_text = page.raw_page_text[source_start:source_end]
        if page.raw_page_text.count(verbatim_text) != 1:
            continue
        return LocatedFragment(
            page_index=page.page_index,
            start_offset=source_start,
            end_offset=source_end,
            verbatim_text=verbatim_text,
        )
    return None


def locate_exact_fragments(
    quote: str,
    *,
    declared_page: object,
    verbatim: VerbatimCorpus,
) -> tuple[LocatedFragment, ...]:
    """Devuelve únicamente fragmentos recuperados literalmente desde el PDF."""

    fragments = split_citation_fragments(quote)
    pages = _page_order(verbatim, declared_page)
    located = tuple(_locate_fragment(fragment, pages) for fragment in fragments)
    if not located or any(item is None for item in located):
        return ()
    exact = tuple(item for item in located if item is not None)
    return tuple(
        sorted(exact, key=lambda item: (item.page_index, item.start_offset, item.end_offset))
    )
