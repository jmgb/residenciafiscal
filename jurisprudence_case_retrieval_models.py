"""Contrato de las unidades recuperables derivadas de un caso v3."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from jurisprudence_case_analysis import BurdenOfProofStep, TreatyAnalysis
from jurisprudence_case_catalogs import (
    CriterionId,
    EvidenceCategory,
    EvidenceParty,
    Identifier,
    IssueOutcome,
    IssueType,
    JurisprudenceCaseModel,
    LegalReviewState,
    NonEmptyText,
    Sha256,
    TechnicalReviewState,
)
from jurisprudence_case_entities import (
    CaseFact,
    IssueHolding,
    LegalIssue,
    LegalRule,
    ResidenceDetermination,
)
from jurisprudence_case_evidence import EvidenceFinding
from jurisprudence_case_source import SourceAnchor
from jurisprudence_case_timeline import PresenceEvent, PresencePeriod


class RetrievalSource(JurisprudenceCaseModel):
    case_resource: NonEmptyText
    case_sha256: Sha256
    source_sha256: Sha256


class RetrievalJudgment(JurisprudenceCaseModel):
    judgment_id: Identifier
    roj: NonEmptyText
    ecli: NonEmptyText
    court: NonEmptyText
    chamber: str | None
    decision_date: date
    tax_years: tuple[int, ...]
    countries: tuple[NonEmptyText, ...]


class RetrievalFacets(JurisprudenceCaseModel):
    issue_type: IssueType
    criterion_ids: tuple[CriterionId, ...]
    countries: tuple[NonEmptyText, ...]
    tax_years: tuple[int, ...]
    evidence_categories: tuple[EvidenceCategory, ...]
    evidence_parties: tuple[EvidenceParty, ...]
    outcome: IssueOutcome
    residence_determination: ResidenceDetermination | None = None
    has_treaty: bool
    technical_review: TechnicalReviewState
    legal_review: LegalReviewState


class RetrievalUnit(JurisprudenceCaseModel):
    unit_id: Identifier
    judgment_id: Identifier
    issue: LegalIssue
    holding: IssueHolding
    facts: tuple[CaseFact, ...]
    evidence_findings: tuple[EvidenceFinding, ...]
    legal_rules: tuple[LegalRule, ...]
    burden_of_proof_steps: tuple[BurdenOfProofStep, ...]
    presence_events: tuple[PresenceEvent, ...]
    presence_periods: tuple[PresencePeriod, ...]
    treaty_analyses: tuple[TreatyAnalysis, ...]
    source_anchors: Annotated[tuple[SourceAnchor, ...], Field(min_length=1)]
    facets: RetrievalFacets
    search_text: NonEmptyText


class RetrievalIndex(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-retrieval/1"]
    source: RetrievalSource
    judgment: RetrievalJudgment
    units: Annotated[tuple[RetrievalUnit, ...], Field(min_length=1)]
