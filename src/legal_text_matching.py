"""Normalización y similitud textual para citas jurídicas."""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

MIN_FRAGMENT_LENGTH = 12

_ELLIPSIS_RE = re.compile(r"(?:\[\s*(?:…|\.{2,})\s*\]|\(\s*(?:…|\.{2,})\s*\)|…|\.{2,})")
_PAGE_NUMBER_RE = re.compile(r"\d+")
_END_OF_LINE_HYPHEN_RE = re.compile(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)")
_NON_ALPHANUMERIC_RE = re.compile(r"[\W_]+", flags=re.UNICODE)


def _dehyphenation_skip_indexes(text: str) -> set[int]:
    return {
        index
        for match in _END_OF_LINE_HYPHEN_RE.finditer(text)
        for index in range(match.start(), match.end())
    }


def normalize_legal_text_with_spans(
    text: str,
) -> tuple[str, tuple[tuple[int, int], ...]]:
    """Normaliza para matching conservando el origen de cada carácter resultante."""

    skip_indexes = _dehyphenation_skip_indexes(text)
    characters: list[str] = []
    spans: list[tuple[int, int]] = []
    for source_index, source_character in enumerate(text):
        if source_index in skip_indexes:
            continue
        compatible = unicodedata.normalize("NFKC", source_character).casefold()
        for character in unicodedata.normalize("NFKD", compatible):
            if unicodedata.combining(character):
                continue
            normalized = " " if _NON_ALPHANUMERIC_RE.fullmatch(character) else character
            if normalized == " " and characters and characters[-1] == " ":
                spans[-1] = (spans[-1][0], source_index + 1)
                continue
            characters.append(normalized)
            spans.append((source_index, source_index + 1))

    while characters and characters[0] == " ":
        characters.pop(0)
        spans.pop(0)
    while characters and characters[-1] == " ":
        characters.pop()
        spans.pop()
    return "".join(characters), tuple(spans)


def normalize_legal_text(text: str) -> str:
    """Normaliza diferencias editoriales y de extracción sin reescribir palabras."""

    normalized, _spans = normalize_legal_text_with_spans(text)
    return normalized


def extract_verbatim_fragment(normalized_fragment: str, source_text: str) -> str | None:
    """Recupera del texto fuente un match exacto normalizado sin reconstruirlo."""

    normalized_source, spans = normalize_legal_text_with_spans(source_text)
    start = normalized_source.find(normalized_fragment)
    if start < 0:
        return None
    end = start + len(normalized_fragment)
    source_start = spans[start][0]
    source_end = spans[end - 1][1]
    return source_text[source_start:source_end]


def split_citation_fragments(quote: str) -> tuple[str, ...]:
    """Divide por elipsis y conserva únicamente fragmentos discriminantes."""

    fragments = tuple(
        normalized
        for raw_fragment in _ELLIPSIS_RE.split(quote)
        if len(normalized := normalize_legal_text(raw_fragment)) >= MIN_FRAGMENT_LENGTH
    )
    if fragments:
        return fragments

    normalized_quote = normalize_legal_text(quote)
    return (normalized_quote,) if normalized_quote else ()


def parse_page_number(value: object) -> int | None:
    """Obtiene el primer entero de formatos como ``3`` o ``PÁGINA 3``."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str):
        return None

    match = _PAGE_NUMBER_RE.search(value)
    if not match:
        return None
    page_number = int(match.group())
    return page_number if page_number > 0 else None


def score_fragment(fragment: str, page_text: str) -> tuple[float, bool]:
    """Devuelve similitud parcial y si la coincidencia normalizada es exacta."""

    if not fragment or not page_text:
        return 0.0, False
    if fragment in page_text:
        return 100.0, True
    return float(fuzz.partial_ratio(fragment, page_text)), False
