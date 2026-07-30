"""Secuencias procesales y de convenio del contrato jurisprudencial v3."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from jurisprudence_case_catalogs import (
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
    ProofParty,
    TieBreakerCriterion,
)
from jurisprudence_case_source import ReviewStatus


class BurdenOfProofStep(JurisprudenceCaseModel):
    step_id: Identifier
    sequence: Annotated[int, Field(gt=0)]
    issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    fact_to_prove: NonEmptyText
    initial_bearer: ProofParty
    triggering_evidence_ids: tuple[Identifier, ...]
    shifts_to: ProofParty | None = None
    response_required: str | None = None
    conclusion: NonEmptyText
    anchor_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    review: ReviewStatus


class TreatyTieBreakerStep(JurisprudenceCaseModel):
    step_id: Identifier
    sequence: Annotated[int, Field(gt=0)]
    criterion: TieBreakerCriterion
    applied: bool
    conclusion: NonEmptyText
    fact_ids: tuple[Identifier, ...]
    evidence_ids: tuple[Identifier, ...]
    anchor_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    review: ReviewStatus


class TreatyAnalysis(JurisprudenceCaseModel):
    treaty_analysis_id: Identifier
    countries: Annotated[tuple[NonEmptyText, ...], Field(min_length=2)]
    treaty_citation: NonEmptyText
    domestic_law_issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    dual_residence_established: bool | None
    steps: tuple[TreatyTieBreakerStep, ...]
    decisive_step_id: Identifier | None = None
    result_country: str | None = None
    anchor_ids: tuple[Identifier, ...]
    review: ReviewStatus

    @model_validator(mode="after")
    def validate_steps(self) -> Self:
        step_ids = tuple(step.step_id for step in self.steps)
        duplicate_ids = sorted({step_id for step_id in step_ids if step_ids.count(step_id) > 1})
        if duplicate_ids:
            raise ValueError(f"steps contiene IDs duplicados: {duplicate_ids}")
        sequences = sorted(step.sequence for step in self.steps)
        if sequences != list(range(1, len(sequences) + 1)):
            raise ValueError("steps debe tener una secuencia contigua desde 1")
        if self.decisive_step_id is None:
            return self
        if self.decisive_step_id not in set(step_ids):
            raise ValueError(f"decisive_step_id inexistente: {self.decisive_step_id}")
        return self
