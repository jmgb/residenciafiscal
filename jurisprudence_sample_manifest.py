"""Contrato del manifiesto reproducible de la muestra jurisprudencial v3."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from jurisprudence_case_catalogs import (
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)
from okf_provenance import sha256_file


def _portable_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("se exige una ruta relativa y portable")
    return value


class JurisprudenceSampleDocument(JurisprudenceCaseModel):
    """Entradas humanas y documentales necesarias para construir un caso."""

    judgment_id: Identifier
    source_file: NonEmptyText
    source_sha256: Sha256
    proposal_path: NonEmptyText
    evaluation_path: NonEmptyText

    _validate_source_file = field_validator("source_file")(_portable_relative_path)
    _validate_proposal_path = field_validator("proposal_path")(_portable_relative_path)
    _validate_evaluation_path = field_validator("evaluation_path")(_portable_relative_path)


class JurisprudenceSampleManifest(JurisprudenceCaseModel):
    """Selección congelada, ordenada y sin duplicados."""

    schema_version: Literal["residenciafiscal-jurisprudence-sample/1"]
    sample_id: Identifier
    expected_documents: Annotated[int, Field(gt=0)]
    documents: Annotated[
        tuple[JurisprudenceSampleDocument, ...],
        Field(min_length=1),
    ]

    @model_validator(mode="after")
    def validate_documents(self) -> Self:
        if self.expected_documents != len(self.documents):
            raise ValueError("expected_documents no coincide con documents")
        judgment_ids = tuple(item.judgment_id for item in self.documents)
        if len(judgment_ids) != len(set(judgment_ids)):
            raise ValueError("documents contiene judgment_id duplicado")
        source_files = tuple(item.source_file for item in self.documents)
        if len(source_files) != len(set(source_files)):
            raise ValueError("documents contiene source_file duplicado")
        return self


def load_sample_manifest(path: Path) -> JurisprudenceSampleManifest:
    """Carga y valida el manifiesto sin tolerar campos desconocidos."""

    return JurisprudenceSampleManifest.model_validate_json(path.read_bytes())


def _resolve_input(project_root: Path, source_path: str) -> Path:
    root = project_root.resolve()
    path = (root / source_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"ruta fuera de project_root: {source_path}")
    if not path.is_file():
        raise ValueError(f"entrada inexistente: {source_path}")
    return path


def validate_sample_inputs(
    manifest: JurisprudenceSampleManifest,
    *,
    project_root: Path,
) -> tuple[str, ...]:
    """Comprueba presencia y hash del PDF antes de iniciar el lote."""

    for document in manifest.documents:
        source = _resolve_input(project_root, document.source_file)
        _resolve_input(project_root, document.proposal_path)
        _resolve_input(project_root, document.evaluation_path)
        if sha256_file(source) != document.source_sha256:
            raise ValueError(f"{document.judgment_id}.source_sha256 no coincide con el PDF")
    return tuple(item.judgment_id for item in manifest.documents)
