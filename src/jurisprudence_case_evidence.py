"""Prueba y documentación extranjera del contrato jurisprudencial v3."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from jurisprudence_case_catalogs import (
    EvidenceAssessment,
    EvidenceCategory,
    EvidenceParty,
    EvidenceRole,
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
)
from jurisprudence_case_source import ReviewStatus


class ForeignDocumentType(StrEnum):
    TAX_RESIDENCE_CERTIFICATE = "TAX_RESIDENCE_CERTIFICATE"
    TAX_RETURN = "TAX_RETURN"
    TAX_ASSESSMENT = "TAX_ASSESSMENT"
    TAX_PAYMENT_CERTIFICATE = "TAX_PAYMENT_CERTIFICATE"
    ADMINISTRATIVE_REGISTRATION = "ADMINISTRATIVE_REGISTRATION"
    PRIVATE_CONTRACT = "PRIVATE_CONTRACT"
    OTHER = "OTHER"


class DocumentNature(StrEnum):
    TAX = "TAX"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    PRIVATE = "PRIVATE"
    OTHER = "OTHER"


class TaxScope(StrEnum):
    WORLDWIDE_INCOME = "WORLDWIDE_INCOME"
    SOURCE_INCOME = "SOURCE_INCOME"
    RESIDENCE_ONLY = "RESIDENCE_ONLY"
    NOT_STATED = "NOT_STATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ForeignDocumentDetails(JurisprudenceCaseModel):
    document_type: ForeignDocumentType
    issuing_authority: str | None = None
    jurisdiction: NonEmptyText
    period_start: date | None = None
    period_end: date | None = None
    nature: DocumentNature
    tax_scope: TaxScope
    defects: tuple[NonEmptyText, ...]
    probative_effect: NonEmptyText

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end no puede preceder a period_start")
        return self


class EvidenceFinding(JurisprudenceCaseModel):
    evidence_id: Identifier
    offered_by: EvidenceParty
    category: EvidenceCategory
    subtype: NonEmptyText
    description: NonEmptyText
    probative_purpose: NonEmptyText
    fact_ids: tuple[Identifier, ...]
    issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    assessment: EvidenceAssessment
    assessment_reason: str | None = None
    role: EvidenceRole
    foreign_document: ForeignDocumentDetails | None = None
    anchor_ids: tuple[Identifier, ...]
    review: ReviewStatus

    @model_validator(mode="after")
    def validate_judicial_assessment(self) -> Self:
        if self.assessment in {
            EvidenceAssessment.UNRESOLVED,
            EvidenceAssessment.NOT_ASSESSED,
        }:
            return self
        if not self.assessment_reason:
            raise ValueError("assessment_reason es obligatorio para una valoración judicial")
        if not self.anchor_ids:
            raise ValueError("anchor_ids es obligatorio para una valoración judicial")
        return self

    @model_validator(mode="after")
    def validate_foreign_document(self) -> Self:
        is_foreign_document = self.category == EvidenceCategory.FOREIGN_TAX_DOCUMENTATION
        if is_foreign_document and self.foreign_document is None:
            raise ValueError("foreign_document es obligatorio para documentación fiscal extranjera")
        if not is_foreign_document and self.foreign_document is not None:
            raise ValueError("foreign_document solo se admite para documentación fiscal extranjera")
        return self
