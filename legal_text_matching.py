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


def normalize_legal_text(text: str) -> str:
    """Normaliza diferencias editoriales y de extracción sin reescribir palabras."""

    dehyphenated = _END_OF_LINE_HYPHEN_RE.sub("", text)
    compatibility_normalized = unicodedata.normalize("NFKC", dehyphenated).casefold()
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", compatibility_normalized)
        if not unicodedata.combining(character)
    )
    return _NON_ALPHANUMERIC_RE.sub(" ", without_accents).strip()


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
