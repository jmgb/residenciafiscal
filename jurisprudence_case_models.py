"""Agregado raíz del contrato `residenciafiscal-case/3`."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from jurisprudence_case_analysis import BurdenOfProofStep, TreatyAnalysis
from jurisprudence_case_catalogs import JurisprudenceCaseModel
from jurisprudence_case_entities import (
    CaseFact,
    IssueHolding,
    LegalIssue,
    LegalRule,
)
from jurisprudence_case_evidence import EvidenceFinding
from jurisprudence_case_source import JudgmentIdentity, ReviewStatus, SourceAnchor
from jurisprudence_case_timeline import PresenceEvent, PresencePeriod
from jurisprudence_case_validation import validate_jurisprudence_case

CASE_SCHEMA_VERSION = "residenciafiscal-case/3"


class JurisprudenceCase(JurisprudenceCaseModel):
    """Caso jurisprudencial validado y listo para consumidores derivados."""

    schema_version: Literal["residenciafiscal-case/3"]
    judgment: JudgmentIdentity
    legal_issues: Annotated[tuple[LegalIssue, ...], Field(min_length=1)]
    facts: tuple[CaseFact, ...]
    evidence_findings: tuple[EvidenceFinding, ...]
    legal_rules: tuple[LegalRule, ...]
    holdings: Annotated[tuple[IssueHolding, ...], Field(min_length=1)]
    burden_of_proof_steps: tuple[BurdenOfProofStep, ...]
    presence_events: tuple[PresenceEvent, ...]
    presence_periods: tuple[PresencePeriod, ...]
    treaty_analyses: tuple[TreatyAnalysis, ...]
    source_anchors: Annotated[tuple[SourceAnchor, ...], Field(min_length=1)]
    review: ReviewStatus

    @model_validator(mode="after")
    def validate_relations(self) -> Self:
        validate_jurisprudence_case(self)
        return self
