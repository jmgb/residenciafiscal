"""Extracción de páginas PDF y detección conservadora de su etiqueta impresa."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from citation_models import ExtractedPage

_PRINTED_PAGE_RE = re.compile(r"^(?:\d{1,4}|[ivxlcdm]{1,8})$", flags=re.IGNORECASE)


def detect_printed_page_label(page_text: str) -> str | None:
    """Detecta una etiqueta aislada al final; no infiere offsets si no existe."""

    lines = tuple(line.strip() for line in page_text.splitlines() if line.strip())
    if not lines:
        return None
    candidate = lines[-1]
    return candidate if _PRINTED_PAGE_RE.fullmatch(candidate) else None


def extract_pdf_pages(pdf_path: Path) -> tuple[ExtractedPage, ...]:
    """Extrae texto, índice físico 1-based y etiqueta impresa de cada página."""

    reader = PdfReader(str(pdf_path))
    extracted: list[ExtractedPage] = []
    for pdf_page_index, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").replace("\x00", " ").strip()
        extracted.append(
            ExtractedPage(
                pdf_page_index=pdf_page_index,
                printed_page_label=detect_printed_page_label(text),
                text=text,
            )
        )
    return tuple(extracted)
