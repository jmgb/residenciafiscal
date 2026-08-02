"""Creación controlada y reanudable de stores PDF jurisprudenciales."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import Field, model_validator

from jurisprudence_case_catalogs import (
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)
from jurisprudence_rollout import load_rollout_manifest
from jurisprudence_rollout_models import RolloutDocument
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
    schema_version: Literal[
        "residenciafiscal-file-search-store/1",
        "residenciafiscal-file-search-store/2",
    ] = "residenciafiscal-file-search-store/2"
    store_name: NonEmptyText
    manifest_sha256: Sha256 | None = None
    expected_documents: int | None = Field(default=None, ge=1, le=106)
    status: Literal["PREPARING", "ACTIVE"] = "ACTIVE"
    documents: Annotated[tuple[StoreDocumentReceipt, ...], Field(max_length=106)] = ()

    @model_validator(mode="after")
    def validate_completion(self) -> StoreReceipt:
        if self.status == "ACTIVE" and self.expected_documents is not None:
            if len(self.documents) != self.expected_documents:
                raise ValueError("un store ACTIVE debe contener todos los documentos esperados")
        return self


ManifestDocument = JurisprudenceSampleDocument | RolloutDocument


def _validated_documents(
    manifest_path: Path,
    project_root: Path,
) -> tuple[ManifestDocument, ...]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version == "residenciafiscal-jurisprudence-sample/1":
        documents: tuple[ManifestDocument, ...] = load_sample_manifest(manifest_path).documents
    elif schema_version == "residenciafiscal-rollout/1":
        documents = load_rollout_manifest(manifest_path).documents
    else:
        raise ValueError("schema de manifiesto no compatible con File Search")
    for document in documents:
        source = project_root / document.source_file
        if not source.is_file():
            raise ValueError(f"PDF inexistente: {document.source_file}")
        if sha256_file(source) != document.source_sha256:
            raise ValueError(f"{document.judgment_id}.source_sha256 no coincide con el PDF")
    return documents


def _display_name(manifest_path: Path, document_count: int) -> str:
    if document_count == 5 and "sample" in manifest_path.stem:
        return STORE_DISPLAY_NAME
    return f"residenciafiscal-rollout-{document_count}-authority-v2"


def _preparing_state(
    *,
    store_name: str,
    manifest_sha256: str,
    expected_documents: int,
    receipts: tuple[StoreDocumentReceipt, ...],
) -> StoreReceipt:
    return StoreReceipt(
        schema_version="residenciafiscal-file-search-store/2",
        store_name=store_name,
        manifest_sha256=manifest_sha256,
        expected_documents=expected_documents,
        status="PREPARING",
        documents=receipts,
    )


def _validate_resume(
    state: StoreReceipt,
    *,
    manifest_sha256: str,
    documents: tuple[ManifestDocument, ...],
) -> None:
    if state.manifest_sha256 != manifest_sha256 or state.expected_documents != len(documents):
        raise ValueError("el checkpoint no corresponde al manifiesto")
    expected_prefix = tuple(
        (item.judgment_id, item.source_file, item.source_sha256, "ACTIVE")
        for item in documents[: len(state.documents)]
    )
    actual_prefix = tuple(
        (item.judgment_id, item.source_file, item.source_sha256, item.status)
        for item in state.documents
    )
    if actual_prefix != expected_prefix:
        raise ValueError("los documentos del checkpoint no coinciden con el manifiesto")


def prepare_file_search_store(
    *,
    gateway: StoreGateway,
    manifest_path: Path,
    project_root: Path,
    existing_state: StoreReceipt | None = None,
    checkpoint: Callable[[StoreReceipt], None] | None = None,
) -> StoreReceipt:
    """Sube un manifiesto validado y conserva un checkpoint tras cada PDF."""

    documents = _validated_documents(manifest_path, project_root)
    manifest_hash = sha256_file(manifest_path)
    created_here = existing_state is None
    if existing_state is None:
        store_name = gateway.create_store(_display_name(manifest_path, len(documents)))
        state = _preparing_state(
            store_name=store_name,
            manifest_sha256=manifest_hash,
            expected_documents=len(documents),
            receipts=(),
        )
        if checkpoint:
            checkpoint(state)
    else:
        _validate_resume(existing_state, manifest_sha256=manifest_hash, documents=documents)
        state = existing_state
        store_name = state.store_name
    if state.status == "ACTIVE":
        return state

    receipts = list(state.documents)
    try:
        for document in documents[len(receipts) :]:
            receipts.append(
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
            )
            state = _preparing_state(
                store_name=store_name,
                manifest_sha256=manifest_hash,
                expected_documents=len(documents),
                receipts=tuple(receipts),
            )
            if checkpoint:
                checkpoint(state)
    except Exception:
        if created_here and checkpoint is None:
            gateway.delete_store(store_name)
        raise
    completed = state.model_copy(update={"status": "ACTIVE"})
    if checkpoint:
        checkpoint(completed)
    return completed


def prepare_sample_store(
    *,
    gateway: StoreGateway,
    manifest_path: Path,
    project_root: Path,
) -> StoreReceipt:
    """Valida toda la muestra antes de crear recursos remotos y subir PDFs."""

    documents = _validated_documents(manifest_path, project_root)
    if len(documents) != 5:
        raise ValueError("F0 exige exactamente cinco PDF")
    return prepare_file_search_store(
        gateway=gateway,
        manifest_path=manifest_path,
        project_root=project_root,
    )
