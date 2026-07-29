"""Procedencia, revisión y anclajes del contrato jurisprudencial v3."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from jurisprudence_case_catalogs import (
    AnchorFidelity,
    AnchorPurpose,
    Identifier,
    JurisprudenceCaseModel,
    LegalReviewState,
    NonEmptyText,
    Sha256,
    TechnicalReviewState,
)


class ReviewStatus(JurisprudenceCaseModel):
    technical: TechnicalReviewState
    legal: LegalReviewState
    reviewed_by: str | None = None
    reviewed_at: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_reviewer_identity(self) -> Self:
        if self.legal == LegalReviewState.AGENT_REVIEWED:
            if self.reviewed_by and self.reviewed_by.startswith("human:"):
                raise ValueError("AGENT_REVIEWED no admite una identidad human:")
            return self
        if self.legal != LegalReviewState.HUMAN_APPROVED:
            return self
        if not self.reviewed_by or not self.reviewed_by.startswith("human:"):
            raise ValueError("HUMAN_APPROVED exige reviewed_by con prefijo human:")
        if self.reviewed_at is None:
            raise ValueError("HUMAN_APPROVED exige reviewed_at")
        return self


class ExtractorIdentity(JurisprudenceCaseModel):
    name: NonEmptyText
    version: NonEmptyText


class AnalysisInputKind(StrEnum):
    VERBATIM = "VERBATIM"
    LEGACY_ANALYSIS = "LEGACY_ANALYSIS"
    ANNOTATIONS = "ANNOTATIONS"
    OTHER = "OTHER"


class AnalysisInputArtifact(JurisprudenceCaseModel):
    kind: AnalysisInputKind
    source_path: NonEmptyText
    sha256: Sha256

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        source = PurePosixPath(value)
        if source.is_absolute() or ".." in source.parts or "\\" in value:
            raise ValueError("source_path debe ser una ruta relativa y portable")
        return value


class AnalysisProvenance(JurisprudenceCaseModel):
    producer: NonEmptyText
    model_id: str | None = None
    prompt_sha256: Sha256 | None = None
    run_id: str | None = None
    generated_at: datetime
    input_artifacts: Annotated[
        tuple[AnalysisInputArtifact, ...],
        Field(min_length=1),
    ]
    notes: str | None = None

    @model_validator(mode="after")
    def validate_verbatim_input(self) -> Self:
        verbatim_count = sum(
            artifact.kind == AnalysisInputKind.VERBATIM for artifact in self.input_artifacts
        )
        if verbatim_count != 1:
            raise ValueError("input_artifacts exige exactamente una entrada VERBATIM")
        return self


class JudgmentIdentity(JurisprudenceCaseModel):
    judgment_id: Identifier
    source_file: NonEmptyText
    roj: NonEmptyText
    ecli: NonEmptyText
    court: NonEmptyText
    chamber: str | None = None
    decision_date: date
    tax_years: tuple[int, ...]
    countries: tuple[NonEmptyText, ...]
    is_tax_residence_case: bool
    source_sha256: Sha256
    page_count: Annotated[int, Field(gt=0)]
    extractor: ExtractorIdentity
    analysis_provenance: AnalysisProvenance
    review: ReviewStatus


class SourceFragment(JurisprudenceCaseModel):
    page_index: Annotated[int, Field(gt=0)]
    printed_page: str | None = None
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(gt=0)]
    verbatim_text: NonEmptyText

    @model_validator(mode="after")
    def validate_offsets(self) -> Self:
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset debe ser mayor que start_offset")
        return self


class SourceAnchor(JurisprudenceCaseModel):
    anchor_id: Identifier
    source_sha256: Sha256
    fragments: Annotated[tuple[SourceFragment, ...], Field(min_length=1)]
    fidelity: AnchorFidelity
    purpose: AnchorPurpose
    review: ReviewStatus

    @model_validator(mode="after")
    def validate_fidelity_and_order(self) -> Self:
        if self.fidelity == AnchorFidelity.EXACT and len(self.fragments) != 1:
            raise ValueError("EXACT exige un fragmento")
        if self.fidelity == AnchorFidelity.EXACT_WITH_ELLIPSIS and len(self.fragments) < 2:
            raise ValueError("EXACT_WITH_ELLIPSIS exige al menos dos fragmentos")
        positions = tuple(
            (fragment.page_index, fragment.start_offset, fragment.end_offset)
            for fragment in self.fragments
        )
        if positions != tuple(sorted(positions)):
            raise ValueError("los fragmentos deben permanecer ordenados por página y offset")
        return self
