"""Contratos del rollout reanudable de jurisprudencia v3."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from jurisprudence_case_catalogs import (
    Identifier,
    JurisprudenceCaseModel,
    LegalReviewState,
    NonEmptyText,
    Sha256,
)


def _portable_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("se exige una ruta relativa y portable")
    return value


class RolloutRisk(StrEnum):
    HIGH = "HIGH"
    STANDARD = "STANDARD"


class RolloutExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    BUILD_PASSED = "BUILD_PASSED"
    BUILD_FAILED = "BUILD_FAILED"


class RolloutDocument(JurisprudenceCaseModel):
    judgment_id: Identifier
    source_file: NonEmptyText
    source_sha256: Sha256
    proposal_path: NonEmptyText
    evaluation_path: NonEmptyText
    batch_id: Identifier
    risk: RolloutRisk

    _validate_source = field_validator("source_file")(_portable_path)
    _validate_proposal = field_validator("proposal_path")(_portable_path)
    _validate_evaluation = field_validator("evaluation_path")(_portable_path)


class RolloutManifest(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-rollout/1"]
    rollout_id: Identifier
    expected_documents: int = Field(gt=0)
    documents: Annotated[tuple[RolloutDocument, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_documents(self) -> Self:
        if self.expected_documents != len(self.documents):
            raise ValueError("expected_documents no coincide con documents")
        ids = tuple(item.judgment_id for item in self.documents)
        if len(ids) != len(set(ids)):
            raise ValueError("documents contiene judgment_id duplicado")
        source_files = tuple(item.source_file for item in self.documents)
        if len(source_files) != len(set(source_files)):
            raise ValueError("documents contiene source_file duplicado")
        seen_batches: set[str] = set()
        current_batch = ""
        for document in self.documents:
            if document.batch_id != current_batch:
                if document.batch_id in seen_batches:
                    raise ValueError("cada batch_id debe ocupar un bloque contiguo")
                seen_batches.add(document.batch_id)
                current_batch = document.batch_id
        return self


class RolloutBuildResult(JurisprudenceCaseModel):
    judgment_id: Identifier
    case_sha256: Sha256
    retrieval_sha256: Sha256
    markdown_sha256: Sha256
    verbatim_sha256: Sha256
    legal_review: LegalReviewState


class RolloutDocumentState(JurisprudenceCaseModel):
    judgment_id: Identifier
    batch_id: Identifier
    risk: RolloutRisk
    attempts: int = Field(ge=0)
    execution_status: RolloutExecutionStatus
    legal_review: LegalReviewState
    case_sha256: Sha256 | None = None
    retrieval_sha256: Sha256 | None = None
    markdown_sha256: Sha256 | None = None
    verbatim_sha256: Sha256 | None = None
    last_error: str | None = None


class RolloutState(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-rollout-state/1"]
    rollout_id: Identifier
    manifest_sha256: Sha256
    documents: Annotated[tuple[RolloutDocumentState, ...], Field(min_length=1)]
