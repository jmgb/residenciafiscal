"""Contrato del manifiesto fijo para muestras de verificación de citas."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SampleDocument(BaseModel):
    """Sentencia incluida y razón observable de su selección."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    archivo: str = Field(min_length=1)
    cubre: tuple[str, ...] = Field(min_length=1)
    motivo: str = Field(min_length=1)


class CitationSampleManifest(BaseModel):
    """Muestra ordenada, versionada y con cardinalidad explícita."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    name: str = Field(min_length=1)
    expected_documents: int = Field(gt=0)
    documents: tuple[SampleDocument, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_document_set(self) -> Self:
        source_files = self.source_files
        if len(source_files) != self.expected_documents:
            raise ValueError("expected_documents no coincide con documents")
        if len(source_files) != len(set(source_files)):
            raise ValueError("el manifiesto contiene archivos duplicados")
        return self

    @property
    def source_files(self) -> tuple[str, ...]:
        return tuple(document.archivo for document in self.documents)


def load_sample_manifest(path: Path) -> CitationSampleManifest:
    """Carga un manifiesto JSON usando validación estricta."""

    return CitationSampleManifest.model_validate_json(path.read_text(encoding="utf-8"))
