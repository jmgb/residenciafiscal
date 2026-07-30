"""Contratos del banco holdout congelado de fase E0."""

from __future__ import annotations

from datetime import date
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_validator

from jurisprudence_case_catalogs import (
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)
from jurisprudence_sample_evaluation_models import ResponseBehavior


def _relative_resource(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("bank_resource debe ser relativo y portable")
    return value


class HoldoutLock(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-holdout-lock/1"]
    bank_resource: NonEmptyText
    bank_sha256: Sha256
    question_count: int = Field(gt=0)
    frozen_on: date
    policy: Literal["NEVER_TUNE_PHASE_D_WITH_THIS_BANK"]

    _validate_bank_resource = field_validator("bank_resource")(_relative_resource)


class HoldoutQuestionResult(JurisprudenceCaseModel):
    question_id: NonEmptyText
    expected_behavior: ResponseBehavior
    predicted_behavior: ResponseBehavior
    retrieved_judgment_ids: tuple[Identifier, ...]
    expected_recall_at_3: float | None
    contrast_recall_at_3: float | None


class HoldoutEvaluationReport(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-holdout-evaluation/1"]
    evaluation_policy: Literal["OBSERVE_ONLY_NO_TUNING"]
    status: Literal["RECORDED"]
    sample_id: Identifier
    lock_sha256: Sha256
    bank_sha256: Sha256
    corpus_sha256: Sha256
    question_count: int
    answerable_question_count: int
    behavior_accuracy: float = Field(ge=0, le=1)
    zero_source_safety: float = Field(ge=0, le=1)
    expected_recall_at_3: float = Field(ge=0, le=1)
    relevant_case_precision_at_3: float = Field(ge=0, le=1)
    contrast_recall_at_3: float = Field(ge=0, le=1)
    results: tuple[HoldoutQuestionResult, ...]
