"""Carga y verificación por lotes de ``frases_clave``."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from citation_verification import (
    CitationStatus,
    CitationVerification,
    verify_citation_pages,
)

PageLoader = Callable[[Path], tuple[str, ...]]
VERIFIED_STATUSES = frozenset(
    {
        CitationStatus.VERIFIED_DECLARED_PAGE,
        CitationStatus.VERIFIED_ADJACENT_PAGE,
        CitationStatus.VERIFIED_OTHER_PAGE,
    }
)


@dataclass(frozen=True)
class CitationCandidate:
    """Una entrada de ``frases_clave`` asociada a su PDF."""

    source_file: str
    citation_index: int
    topic: str
    declared_page: object
    quote: str


@dataclass(frozen=True)
class LoadedCitation:
    """Cita junto con las páginas extraídas o el error de carga."""

    candidate: CitationCandidate
    pages: tuple[str, ...] | None
    error: str | None = None


@dataclass(frozen=True)
class CitationFinding:
    """Resultado del spike para una cita."""

    candidate: CitationCandidate
    verification: CitationVerification | None
    error: str | None = None


def extract_citation_candidates(
    records: Iterable[Mapping[str, object]],
) -> tuple[CitationCandidate, ...]:
    """Extrae entradas utilizables de ``frases_clave`` sin inventar campos."""

    candidates: list[CitationCandidate] = []
    for record in records:
        source_file = record.get("archivo")
        raw_citations = record.get("frases_clave")
        if not isinstance(source_file, str) or not isinstance(raw_citations, list):
            continue

        for citation_index, raw_citation in enumerate(raw_citations):
            if not isinstance(raw_citation, dict):
                continue
            quote = raw_citation.get("texto")
            if not isinstance(quote, str) or not quote.strip():
                continue
            topic = raw_citation.get("tema")
            candidates.append(
                CitationCandidate(
                    source_file=source_file,
                    citation_index=citation_index,
                    topic=topic if isinstance(topic, str) else "",
                    declared_page=raw_citation.get("pagina"),
                    quote=quote.strip(),
                )
            )
    return tuple(candidates)


def extract_pdf_pages(pdf_path: Path) -> tuple[str, ...]:
    """Extrae el texto de un PDF conservando una entrada por página."""

    reader = PdfReader(str(pdf_path))
    return tuple((page.extract_text() or "").replace("\x00", " ").strip() for page in reader.pages)


def load_citation_sources(
    candidates: Sequence[CitationCandidate],
    pdf_dir: Path,
    *,
    page_loader: PageLoader = extract_pdf_pages,
    require_source_file: bool = True,
) -> tuple[LoadedCitation, ...]:
    """Carga cada PDF una sola vez y propaga su resultado a todas sus citas."""

    cache: dict[str, tuple[tuple[str, ...] | None, str | None]] = {}
    loaded: list[LoadedCitation] = []
    for candidate in candidates:
        if candidate.source_file not in cache:
            pdf_path = pdf_dir / candidate.source_file
            if require_source_file and not pdf_path.is_file():
                cache[candidate.source_file] = (None, "source_missing")
            else:
                try:
                    cache[candidate.source_file] = (page_loader(pdf_path), None)
                except Exception as exc:  # El informe debe continuar con el resto del corpus.
                    cache[candidate.source_file] = (
                        None,
                        f"extraction_error:{type(exc).__name__}",
                    )
        pages, error = cache[candidate.source_file]
        loaded.append(LoadedCitation(candidate=candidate, pages=pages, error=error))
    return tuple(loaded)


def verify_loaded_citations(
    loaded_citations: Sequence[LoadedCitation],
    *,
    threshold: float,
) -> tuple[CitationFinding, ...]:
    """Aplica el verificador puro a las fuentes ya extraídas."""

    findings: list[CitationFinding] = []
    for loaded in loaded_citations:
        if loaded.pages is None:
            findings.append(
                CitationFinding(
                    candidate=loaded.candidate,
                    verification=None,
                    error=loaded.error or "unknown_processing_error",
                )
            )
            continue
        findings.append(
            CitationFinding(
                candidate=loaded.candidate,
                verification=verify_citation_pages(
                    quote=loaded.candidate.quote,
                    declared_page=loaded.candidate.declared_page,
                    pages=loaded.pages,
                    threshold=threshold,
                ),
            )
        )
    return tuple(findings)
