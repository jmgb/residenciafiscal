"""Estado reanudable, ejecución por lotes y gates de fase E."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from jurisprudence_case_catalogs import LegalReviewState
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_rollout_models import (
    RolloutBuildResult,
    RolloutDocument,
    RolloutDocumentState,
    RolloutExecutionStatus,
    RolloutManifest,
    RolloutState,
)
from okf_provenance import sha256_file

DocumentExecutor = Callable[[RolloutDocument], RolloutBuildResult]


@dataclass(frozen=True)
class RolloutExecutionResult:
    batch_id: str
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    state_path: Path


def load_rollout_manifest(path: Path) -> RolloutManifest:
    return RolloutManifest.model_validate_json(path.read_bytes())


def load_rollout_state(path: Path) -> RolloutState:
    return RolloutState.model_validate_json(path.read_bytes())


def _render_state(state: RolloutState) -> str:
    return (
        json.dumps(
            state.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_rollout_state(state: RolloutState, path: Path) -> None:
    write_case_derivative(_render_state(state), path)


def initialize_rollout(manifest_path: Path) -> RolloutState:
    manifest = load_rollout_manifest(manifest_path)
    return RolloutState(
        schema_version="residenciafiscal-rollout-state/1",
        rollout_id=manifest.rollout_id,
        manifest_sha256=sha256_file(manifest_path),
        documents=tuple(
            RolloutDocumentState(
                judgment_id=item.judgment_id,
                batch_id=item.batch_id,
                risk=item.risk,
                attempts=0,
                execution_status=RolloutExecutionStatus.PENDING,
                legal_review=LegalReviewState.UNREVIEWED,
            )
            for item in manifest.documents
        ),
    )


def _replace_document(
    state: RolloutState,
    updated: RolloutDocumentState,
) -> RolloutState:
    return state.model_copy(
        update={
            "documents": tuple(
                updated if item.judgment_id == updated.judgment_id else item
                for item in state.documents
            )
        }
    )


def _load_or_initialize(
    manifest_path: Path,
    state_path: Path,
    manifest: RolloutManifest,
) -> RolloutState:
    state = (
        load_rollout_state(state_path)
        if state_path.is_file()
        else initialize_rollout(manifest_path)
    )
    if state.manifest_sha256 != sha256_file(manifest_path):
        raise ValueError("el manifiesto cambió después de iniciar el rollout")
    expected_documents = tuple(
        (item.judgment_id, item.batch_id, item.risk) for item in manifest.documents
    )
    state_documents = tuple(
        (item.judgment_id, item.batch_id, item.risk) for item in state.documents
    )
    if state.rollout_id != manifest.rollout_id or state_documents != expected_documents:
        raise ValueError("los documentos del estado no corresponden al manifiesto")
    return state


def _next_batch(state: RolloutState) -> str | None:
    for item in state.documents:
        if item.execution_status != RolloutExecutionStatus.BUILD_PASSED:
            return item.batch_id
    return None


def execute_next_batch(
    *,
    manifest_path: Path,
    state_path: Path,
    executor: DocumentExecutor,
    retry_failed: bool = False,
) -> RolloutExecutionResult:
    manifest = load_rollout_manifest(manifest_path)
    state = _load_or_initialize(manifest_path, state_path, manifest)
    batch_id = _next_batch(state)
    if batch_id is None:
        raise ValueError("el rollout ya no contiene documentos pendientes")
    batch_states = tuple(item for item in state.documents if item.batch_id == batch_id)
    if (
        any(item.execution_status == RolloutExecutionStatus.BUILD_FAILED for item in batch_states)
        and not retry_failed
    ):
        raise ValueError("el lote contiene fallos; usa retry_failed para reanudarlo")
    documents_by_id = {item.judgment_id: item for item in manifest.documents}
    passed = []
    failed = []
    for current in batch_states:
        if current.execution_status == RolloutExecutionStatus.BUILD_PASSED:
            continue
        if current.execution_status == RolloutExecutionStatus.BUILD_FAILED and not retry_failed:
            continue
        running = current.model_copy(
            update={
                "attempts": current.attempts + 1,
                "execution_status": RolloutExecutionStatus.RUNNING,
                "last_error": None,
            }
        )
        state = _replace_document(state, running)
        write_rollout_state(state, state_path)
        try:
            result = executor(documents_by_id[current.judgment_id])
            if result.judgment_id != current.judgment_id:
                raise ValueError("el judgment_id no coincide con el documento en ejecución")
        except Exception as error:
            failed_state = running.model_copy(
                update={
                    "execution_status": RolloutExecutionStatus.BUILD_FAILED,
                    "last_error": f"{type(error).__name__}: {error}",
                }
            )
            state = _replace_document(state, failed_state)
            write_rollout_state(state, state_path)
            failed.append(current.judgment_id)
            continue
        passed_state = running.model_copy(
            update={
                **result.model_dump(mode="python", exclude={"judgment_id"}),
                "execution_status": RolloutExecutionStatus.BUILD_PASSED,
                "last_error": None,
            }
        )
        state = _replace_document(state, passed_state)
        write_rollout_state(state, state_path)
        passed.append(current.judgment_id)
    return RolloutExecutionResult(
        batch_id=batch_id,
        passed=tuple(passed),
        failed=tuple(failed),
        state_path=state_path,
    )


def batch_gate(state_path: Path, batch_id: str) -> str:
    state = load_rollout_state(state_path)
    documents = tuple(item for item in state.documents if item.batch_id == batch_id)
    if not documents:
        raise ValueError(f"batch_id desconocido: {batch_id}")
    if any(item.execution_status != RolloutExecutionStatus.BUILD_PASSED for item in documents):
        return "BUILD_INCOMPLETE"
    if any(item.legal_review != LegalReviewState.HUMAN_APPROVED for item in documents):
        return "AWAITING_HUMAN_REVIEW"
    return "PASSED"
