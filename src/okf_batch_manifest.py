"""Contrato congelado de entrada para una muestra OKF."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from okf_document_builder import load_unique_record
from okf_provenance import sha256_analysis_record, sha256_file

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class OkfBatchDocument(BaseModel):
    """Hashes de las dos fuentes que alimentan un concepto."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_file: str = Field(min_length=1)
    pdf_sha256: Sha256
    analysis_record_sha256: Sha256


class OkfBatchManifest(BaseModel):
    """Selección explícita, cerrada y validable de sentencias."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    name: str = Field(min_length=1)
    expected_documents: int = Field(gt=0)
    output_schema_version: Literal["residenciafiscal-okf-manifest/3"]
    analysis_jsonl_sha256: Sha256
    documents: tuple[OkfBatchDocument, ...] = Field(min_length=1)

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
        return tuple(document.source_file for document in self.documents)


def load_okf_batch_manifest(path: Path) -> OkfBatchManifest:
    """Carga el manifiesto con validación estricta."""

    return OkfBatchManifest.model_validate_json(path.read_text(encoding="utf-8"))


def validate_batch_sources(
    manifest: OkfBatchManifest,
    jsonl_path: Path,
    pdf_dir: Path,
) -> tuple[str, ...]:
    """Comprueba hashes del JSONL, cada PDF y cada registro canónico."""

    if sha256_file(jsonl_path) != manifest.analysis_jsonl_sha256:
        raise ValueError("El SHA-256 del JSONL no coincide con el manifiesto")
    for document in manifest.documents:
        pdf_path = pdf_dir / document.source_file
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        if sha256_file(pdf_path) != document.pdf_sha256:
            raise ValueError(f"El SHA-256 del PDF no coincide: {document.source_file}")
        record = load_unique_record(jsonl_path, document.source_file)
        if sha256_analysis_record(record) != document.analysis_record_sha256:
            raise ValueError(
                f"El SHA-256 del registro de análisis no coincide: {document.source_file}"
            )
    return tuple(sorted(manifest.source_files))
