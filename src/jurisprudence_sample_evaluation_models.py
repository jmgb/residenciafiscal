"""Contratos del banco y del informe de evaluación de recuperación."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from jurisprudence_case_catalogs import Identifier, JurisprudenceCaseModel, NonEmptyText

ResponseBehavior = Literal["responder", "parcial", "preguntar", "abstenerse"]


class RetrievalEvaluationQuestion(JurisprudenceCaseModel):
    question_id: NonEmptyText
    question: NonEmptyText
    behavior: ResponseBehavior
    expected_judgment_ids: tuple[Identifier, ...]
    contrast_judgment_ids: tuple[Identifier, ...]


class RetrievalEvaluationBank(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-retrieval-evaluation-bank/1"]
    source_resource: NonEmptyText
    questions: Annotated[
        tuple[RetrievalEvaluationQuestion, ...],
        Field(min_length=1),
    ]


class RetrievalEvaluationResult(JurisprudenceCaseModel):
    question_id: NonEmptyText
    expected_behavior: ResponseBehavior
    expected_judgment_ids: tuple[Identifier, ...]
    contrast_judgment_ids: tuple[Identifier, ...]
    retrieved_unit_ids_at_5: tuple[Identifier, ...]
    retrieved_unit_ids_at_12: tuple[Identifier, ...]
    retrieved_judgment_ids_at_5: tuple[Identifier, ...]
    retrieved_judgment_ids_at_12: tuple[Identifier, ...]
    expected_recall_at_5: float | None
    expected_recall_at_12: float | None
    contrast_recall_at_5: float | None
    contrast_recall_at_12: float | None


class RetrievalEvaluationReport(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-retrieval-evaluation-report/2"]
    sample_id: Identifier
    evaluation_scope: Literal["RETRIEVAL_ONLY"]
    chat_behavior_gate: Literal["NOT_EVALUATED"]
    question_count: int
    expected_behavior_counts: dict[ResponseBehavior, int]
    expected_recall_at_5: float
    expected_recall_at_12: float
    contrast_recall_at_5: float
    contrast_recall_at_12: float
    results: tuple[RetrievalEvaluationResult, ...]
