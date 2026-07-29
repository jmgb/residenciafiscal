"""Cronología de presencia y ausencias del contrato jurisprudencial v3."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from jurisprudence_case_catalogs import (
    AssertionParty,
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
    ProceduralFactStatus,
    SubjectRole,
)
from jurisprudence_case_source import ReviewStatus


class PresenceEventType(StrEnum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    OBSERVED_PRESENT = "OBSERVED_PRESENT"
    OBSERVED_ABSENT = "OBSERVED_ABSENT"
    TRAVEL = "TRAVEL"
    TRANSACTION = "TRANSACTION"
    DOCUMENTED_LOCATION = "DOCUMENTED_LOCATION"
    OTHER = "OTHER"


class DatePrecision(StrEnum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"


class PresenceClassification(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    SPORADIC_ABSENCE = "SPORADIC_ABSENCE"
    UNKNOWN = "UNKNOWN"


class PresenceEvent(JurisprudenceCaseModel):
    event_id: Identifier
    event_type: PresenceEventType
    event_date: date
    date_precision: DatePrecision
    country: NonEmptyText
    place: str | None = None
    subject_role: SubjectRole
    asserted_by: AssertionParty
    procedural_status: ProceduralFactStatus
    fact_ids: tuple[Identifier, ...]
    evidence_ids: tuple[Identifier, ...]
    issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    anchor_ids: tuple[Identifier, ...]
    review: ReviewStatus


class PresencePeriod(JurisprudenceCaseModel):
    period_id: Identifier
    classification: PresenceClassification
    start_date: date | None = None
    end_date: date | None = None
    country: NonEmptyText
    day_count: Annotated[int | None, Field(ge=0)] = None
    calculation_method: NonEmptyText
    counted_for_183_day_rule: bool | None = None
    determined_by: AssertionParty
    fact_ids: tuple[Identifier, ...]
    evidence_ids: tuple[Identifier, ...]
    issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    anchor_ids: tuple[Identifier, ...]
    review: ReviewStatus

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date no puede preceder a start_date")
        if self.start_date is None and self.end_date is None and self.day_count is None:
            raise ValueError("el periodo exige fechas o day_count")
        return self
