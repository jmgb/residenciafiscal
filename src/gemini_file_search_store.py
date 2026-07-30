"""Creación controlada del File Search Store de la muestra fija de cinco."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import Field

from jurisprudence_case_catalogs import (
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)
from jurisprudence_sample_manifest import (
    JurisprudenceSampleDocument,
    load_sample_manifest,
)
from okf_provenance import sha256_file

STORE_DISPLAY_NAME = "residenciafiscal-f0-sample-5"


class StoreGateway(Protocol):
    def create_store(self, display_name: str) -> str: ...

    def upload_pdf(
        self,
        *,
        store_name: str,
        source: Path,
        judgment_id: str,
        source_sha256: str,
    ) -> str: ...

    def delete_store(self, store_name: str) -> None: ...


class StoreDocumentReceipt(JurisprudenceCaseModel):
    judgment_id: NonEmptyText
    source_file: NonEmptyText
    source_sha256: Sha256
    remote_document_name: NonEmptyText
    status: Literal["ACTIVE"]


class StoreReceipt(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-file-search-store/1"] = (
        "residenciafiscal-file-search-store/1"
    )
    store_name: NonEmptyText
    documents: Annotated[tuple[StoreDocumentReceipt, ...], Field(min_length=5, max_length=5)]


def _validated_documents(
    manifest_path: Path,
    project_root: Path,
) -> tuple[JurisprudenceSampleDocument, ...]:
    manifest = load_sample_manifest(manifest_path)
    if manifest.expected_documents != 5:
        raise ValueError("F0 exige exactamente cinco PDF")
    for document in manifest.documents:
        source = project_root / document.source_file
        if not source.is_file():
            raise ValueError(f"PDF inexistente: {document.source_file}")
        if sha256_file(source) != document.source_sha256:
            raise ValueError(f"{document.judgment_id}.source_sha256 no coincide con el PDF")
    return manifest.documents


def prepare_sample_store(
    *,
    gateway: StoreGateway,
    manifest_path: Path,
    project_root: Path,
) -> StoreReceipt:
    """Valida toda la muestra antes de crear recursos remotos y subir PDFs."""

    documents = _validated_documents(manifest_path, project_root)
    store_name = gateway.create_store(STORE_DISPLAY_NAME)
    try:
        receipts = tuple(
            StoreDocumentReceipt(
                judgment_id=document.judgment_id,
                source_file=document.source_file,
                source_sha256=document.source_sha256,
                remote_document_name=gateway.upload_pdf(
                    store_name=store_name,
                    source=project_root / document.source_file,
                    judgment_id=document.judgment_id,
                    source_sha256=document.source_sha256,
                ),
                status="ACTIVE",
            )
            for document in documents
        )
    except Exception:
        gateway.delete_store(store_name)
        raise
    return StoreReceipt(store_name=store_name, documents=receipts)
