"""Contratos de la evaluación comparada de la fase D."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from jurisprudence_case_catalogs import Identifier, JurisprudenceCaseModel, NonEmptyText, Sha256
from jurisprudence_sample_evaluation_models import ResponseBehavior


class ParaphraseDefinition(JurisprudenceCaseModel):
    question_id: NonEmptyText
    source_question_id: NonEmptyText
    question: NonEmptyText


class ParaphraseDefinitions(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-retrieval-paraphrases/1"]
    sample_id: Identifier
    questions: Annotated[tuple[ParaphraseDefinition, ...], Field(min_length=1)]


class StrategyMetrics(JurisprudenceCaseModel):
    measured_question_count: int
    expected_recall_at_3: float = Field(ge=0, le=1)
    relevant_case_precision_at_3: float = Field(ge=0, le=1)
    contrast_recall_at_3: float = Field(ge=0, le=1)


class BehaviorMetrics(JurisprudenceCaseModel):
    question_count: int
    behavior_accuracy: float = Field(ge=0, le=1)
    zero_source_safety: float = Field(ge=0, le=1)
    predicted_behavior_counts: dict[ResponseBehavior, int]


class EvaluationInputs(JurisprudenceCaseModel):
    corpus_sha256: Sha256
    original_bank_sha256: Sha256
    paraphrase_bank_sha256: Sha256


class PhaseDQuestionResult(JurisprudenceCaseModel):
    question_id: NonEmptyText
    expected_behavior: ResponseBehavior
    predicted_behavior: ResponseBehavior
    retrieved_judgment_ids: tuple[Identifier, ...]
    expected_recall_at_3: float | None
    contrast_recall_at_3: float | None


class PhaseDEvaluationReport(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-phase-d-evaluation/1"]
    sample_id: Identifier
    evaluation_policy: Literal["GOLD_USED_ONLY_AFTER_RETRIEVAL"]
    inputs: EvaluationInputs
    original: BehaviorMetrics
    paraphrases: BehaviorMetrics
    baseline: StrategyMetrics
    candidate: StrategyMetrics
    embedding_decision: Literal["NOT_REQUIRED_FOR_PILOT", "REQUIRES_EXPERIMENT"]
    gate_status: Literal["PASSED", "FAILED"]
    gate_failures: tuple[str, ...]
    original_results: tuple[PhaseDQuestionResult, ...]
    paraphrase_results: tuple[PhaseDQuestionResult, ...]
