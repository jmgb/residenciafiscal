"""Contrato y gate de cobertura de preguntas sobre un caso v3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field

from jurisprudence_case_catalogs import Identifier, JurisprudenceCaseModel, NonEmptyText
from jurisprudence_case_models import JurisprudenceCase


class QuestionCoverage(JurisprudenceCaseModel):
    question_id: NonEmptyText
    question: NonEmptyText
    required_issue_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    required_fact_ids: tuple[Identifier, ...]
    required_evidence_ids: tuple[Identifier, ...]
    required_anchor_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    expected_behavior: NonEmptyText
    limitations: NonEmptyText


class CaseQuestionEvaluation(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-case-question-evaluation/1"]
    judgment_id: Identifier
    questions: Annotated[tuple[QuestionCoverage, ...], Field(min_length=1)]


@dataclass(frozen=True)
class QuestionEvaluationResult:
    judgment_id: str
    question_count: int
    question_ids: tuple[str, ...]


def _require_known(
    question_id: str,
    field_name: str,
    required_ids: tuple[str, ...],
    available_ids: set[str],
) -> None:
    missing = set(required_ids) - available_ids
    if missing:
        raise ValueError(f"{question_id}.{field_name}: {sorted(missing)}")


def validate_question_evaluation(
    evaluation: CaseQuestionEvaluation,
    case: JurisprudenceCase,
) -> QuestionEvaluationResult:
    """Comprueba que cada pregunta puede navegar hasta proposiciones citables."""

    if evaluation.judgment_id != case.judgment.judgment_id:
        raise ValueError("judgment_id de evaluación y caso no coincide")
    question_ids = tuple(item.question_id for item in evaluation.questions)
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("questions contiene IDs duplicados")

    available = {
        "required_issue_ids": {item.issue_id for item in case.legal_issues},
        "required_fact_ids": {item.fact_id for item in case.facts},
        "required_evidence_ids": {item.evidence_id for item in case.evidence_findings},
        "required_anchor_ids": {item.anchor_id for item in case.source_anchors},
    }
    for question in evaluation.questions:
        for field_name, available_ids in available.items():
            _require_known(
                question.question_id,
                field_name,
                getattr(question, field_name),
                available_ids,
            )
    return QuestionEvaluationResult(
        judgment_id=evaluation.judgment_id,
        question_count=len(evaluation.questions),
        question_ids=question_ids,
    )
