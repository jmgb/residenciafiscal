"""Adaptador de pypdf para `residenciafiscal-verbatim/1`."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Protocol

from pypdf import PdfReader

from okf_provenance import sha256_file
from pdf_page_extraction import detect_printed_page_label
from verbatim_hashing import sha256_canonical_pages, sha256_utf8
from verbatim_models import (
    PageExtractionStatus,
    VerbatimCorpus,
    VerbatimCorpusStatus,
    VerbatimPage,
)


class ExtractablePage(Protocol):
    def extract_text(self) -> str | None: ...


class PageReader(Protocol):
    @property
    def pages(self) -> Sequence[ExtractablePage]: ...


ReaderFactory = Callable[[str], PageReader]


def _pypdf_reader(source: str) -> PageReader:
    return PdfReader(source)


def _build_page(page_index: int, extracted_text: str | None) -> VerbatimPage:
    if extracted_text is None:
        raw_page_text = ""
        extraction_status = PageExtractionStatus.NO_TEXT_RETURNED
    else:
        raw_page_text = extracted_text
        extraction_status = (
            PageExtractionStatus.EMPTY_TEXT
            if extracted_text == ""
            else PageExtractionStatus.TEXT_EXTRACTED
        )
    return VerbatimPage(
        page_index=page_index,
        printed_page=detect_printed_page_label(raw_page_text),
        raw_page_text=raw_page_text,
        text_sha256=sha256_utf8(raw_page_text),
        extraction_status=extraction_status,
    )


def extract_verbatim_corpus(
    pdf_path: Path,
    *,
    document_id: str,
    source_file: str,
    reader_factory: ReaderFactory = _pypdf_reader,
    extractor_version: str | None = None,
) -> VerbatimCorpus:
    """Extrae páginas sin modificar la cadena devuelta por pypdf."""

    reader = reader_factory(str(pdf_path))
    pages = tuple(
        _build_page(page_index, page.extract_text())
        for page_index, page in enumerate(reader.pages, 1)
    )
    page_records = [page.model_dump(mode="json") for page in pages]
    status = (
        VerbatimCorpusStatus.COMPLETE
        if all(page.extraction_status == PageExtractionStatus.TEXT_EXTRACTED for page in pages)
        else VerbatimCorpusStatus.NEEDS_REVIEW
    )
    return VerbatimCorpus(
        schema_version="residenciafiscal-verbatim/1",
        document_id=document_id,
        source_file=source_file,
        source_sha256=sha256_file(pdf_path),
        extractor={
            "name": "pypdf",
            "version": extractor_version or version("pypdf"),
        },
        page_count=len(pages),
        pages_sha256=sha256_canonical_pages(page_records),
        status=status,
        pages=pages,
    )
