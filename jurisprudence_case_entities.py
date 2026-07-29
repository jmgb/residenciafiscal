"""Hechos, pruebas, normas y cuestiones del análisis jurisprudencial v3."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Self

from pydantic import Field, model_validator

from jurisprudence_case_catalogs import (
    AssertionParty,
    CriterionId,
    FactCategory,
    Identifier,
    IssueOutcome,
    IssueType,
    JurisprudenceCaseModel,
    LegalRuleType,
    NonEmptyText,
    ProceduralFactStatus,
    SubjectRole,
)
from jurisprudence_case_source import ReviewStatus


class CaseFact(JurisprudenceCaseModel):
    fact_id: Identifier
    subject_role: SubjectRole
    category: FactCategory
    description: NonEmptyText
    country: str | None = None
    place: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    tax_years: tuple[int, ...]
    asserted_by: AssertionParty
    procedural_status: ProceduralFactStatus
    issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    anchor_ids: tuple[Identifier, ...]
    review: ReviewStatus

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date no puede preceder a start_date")
        return self

    @model_validator(mode="after")
    def validate_proven_fact_source(self) -> Self:
        is_court_proven = (
            self.asserted_by == AssertionParty.COURT
            and self.procedural_status == ProceduralFactStatus.PROVEN
        )
        if is_court_proven and not self.anchor_ids:
            raise ValueError("anchor_ids es obligatorio para un hecho probado por el tribunal")
        return self


class LegalRule(JurisprudenceCaseModel):
    legal_rule_id: Identifier
    rule_type: LegalRuleType
    citation: NonEmptyText
    proposition: NonEmptyText
    issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    anchor_ids: tuple[Identifier, ...]
    review: ReviewStatus


class IssueHolding(JurisprudenceCaseModel):
    holding_id: Identifier
    issue_id: Identifier
    outcome: IssueOutcome
    conclusion: NonEmptyText
    decisive_reasoning: NonEmptyText
    consequences: tuple[NonEmptyText, ...]
    anchor_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    review: ReviewStatus


class LegalIssue(JurisprudenceCaseModel):
    issue_id: Identifier
    question: NonEmptyText
    issue_type: IssueType
    criterion_ids: tuple[CriterionId, ...]
    fact_ids: tuple[Identifier, ...]
    evidence_ids: tuple[Identifier, ...]
    legal_rule_ids: tuple[Identifier, ...]
    holding_id: Identifier
    anchor_ids: tuple[Identifier, ...]
    review: ReviewStatus
