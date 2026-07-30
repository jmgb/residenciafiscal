"""Modelos de `residenciafiscal-verbatim/1`."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from verbatim_hashing import sha256_canonical_pages, sha256_utf8

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=1),
]
NonEmptyText = Annotated[str, StringConstraints(min_length=1)]


class VerbatimModel(BaseModel):
    """Configuración estricta común del contrato verbatim."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PageExtractionStatus(StrEnum):
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    EMPTY_TEXT = "EMPTY_TEXT"
    NO_TEXT_RETURNED = "NO_TEXT_RETURNED"


class VerbatimCorpusStatus(StrEnum):
    COMPLETE = "COMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class VerbatimExtractorIdentity(VerbatimModel):
    name: NonEmptyText
    version: NonEmptyText


class VerbatimPage(VerbatimModel):
    page_index: Annotated[int, Field(gt=0)]
    printed_page: str | None
    raw_page_text: str
    text_sha256: Sha256
    extraction_status: PageExtractionStatus

    @model_validator(mode="after")
    def validate_text_integrity(self) -> Self:
        if self.text_sha256 != sha256_utf8(self.raw_page_text):
            raise ValueError("text_sha256 no corresponde a raw_page_text")
        text_is_empty = self.raw_page_text == ""
        status_says_empty = self.extraction_status != PageExtractionStatus.TEXT_EXTRACTED
        if text_is_empty != status_says_empty:
            raise ValueError("extraction_status no corresponde a raw_page_text")
        return self


class VerbatimCorpus(VerbatimModel):
    schema_version: Literal["residenciafiscal-verbatim/1"]
    document_id: Identifier
    source_file: NonEmptyText
    source_sha256: Sha256
    extractor: VerbatimExtractorIdentity
    page_count: Annotated[int, Field(gt=0)]
    pages_sha256: Sha256
    status: VerbatimCorpusStatus
    pages: Annotated[tuple[VerbatimPage, ...], Field(min_length=1)]

    @field_validator("source_file")
    @classmethod
    def validate_source_file(cls, value: str) -> str:
        source = PurePosixPath(value)
        invalid = (
            source.is_absolute()
            or ".." in source.parts
            or "\\" in value
            or source.suffix.lower() != ".pdf"
        )
        if invalid:
            raise ValueError("source_file debe ser una ruta PDF relativa y portable")
        return value

    @model_validator(mode="after")
    def validate_pages(self) -> Self:
        if self.page_count != len(self.pages):
            raise ValueError("page_count no coincide con pages")
        indexes = [page.page_index for page in self.pages]
        if indexes != list(range(1, len(self.pages) + 1)):
            raise ValueError("pages debe tener índices contiguos desde 1")
        page_records = [page.model_dump(mode="json") for page in self.pages]
        if self.pages_sha256 != sha256_canonical_pages(page_records):
            raise ValueError("pages_sha256 no corresponde al array canónico de páginas")
        has_extraction_gap = any(
            page.extraction_status != PageExtractionStatus.TEXT_EXTRACTED for page in self.pages
        )
        expected_status = (
            VerbatimCorpusStatus.NEEDS_REVIEW
            if has_extraction_gap
            else VerbatimCorpusStatus.COMPLETE
        )
        if self.status != expected_status:
            raise ValueError("status no corresponde al estado de sus páginas")
        return self
