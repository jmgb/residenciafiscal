"""Adaptador entre el estado reanudable y el pipeline v3 real."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from export_jurisprudence_sample import (
    export_jurisprudence_document,
    sample_document_paths,
)
from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_catalogs import LegalReviewState
from jurisprudence_rollout import RolloutExecutionResult, execute_next_batch
from jurisprudence_rollout_models import (
    RolloutBuildResult,
    RolloutDocument,
)
from jurisprudence_sample_manifest import JurisprudenceSampleDocument
from okf_provenance import sha256_file


def _objects(value: object) -> Iterator[dict[str, object]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _objects(nested)


def _aggregate_legal_review(case_path: Path) -> LegalReviewState:
    case = load_jurisprudence_case(case_path.read_bytes())
    reviews = tuple(
        item["legal"]
        for item in _objects(case.model_dump(mode="json"))
        if {"technical", "legal"} <= set(item)
    )
    if reviews and all(item == "HUMAN_APPROVED" for item in reviews):
        return LegalReviewState.HUMAN_APPROVED
    if "REJECTED" in reviews:
        return LegalReviewState.REJECTED
    if "UNREVIEWED" in reviews:
        return LegalReviewState.UNREVIEWED
    return LegalReviewState.AGENT_REVIEWED


def _validate_residence_determinations(case_path: Path) -> None:
    case = load_jurisprudence_case(case_path.read_bytes())
    holdings = {item.holding_id: item for item in case.holdings}
    missing = tuple(
        issue.issue_id
        for issue in case.legal_issues
        if issue.issue_type == "TAX_RESIDENCE"
        and holdings[issue.holding_id].residence_determination is None
    )
    if missing:
        raise ValueError(f"residence_determination es obligatoria en el rollout: {missing}")


def _resolve_input(project_root: Path, resource: str) -> Path:
    root = project_root.resolve()
    path = (root / resource).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"ruta fuera de project_root: {resource}")
    if not path.is_file():
        raise ValueError(f"entrada inexistente: {resource}")
    return path


def _sample_document(document: RolloutDocument) -> JurisprudenceSampleDocument:
    return JurisprudenceSampleDocument(
        judgment_id=document.judgment_id,
        source_file=document.source_file,
        source_sha256=document.source_sha256,
        proposal_path=document.proposal_path,
        evaluation_path=document.evaluation_path,
    )


def _build_document(
    document: RolloutDocument,
    *,
    output_root: Path,
    project_root: Path,
) -> RolloutBuildResult:
    source = _resolve_input(project_root, document.source_file)
    _resolve_input(project_root, document.proposal_path)
    _resolve_input(project_root, document.evaluation_path)
    if sha256_file(source) != document.source_sha256:
        raise ValueError(f"{document.judgment_id}.source_sha256 no coincide")
    sample_document = _sample_document(document)
    result = export_jurisprudence_document(
        sample_document,
        output_root=output_root,
        project_root=project_root,
    )
    paths = sample_document_paths(
        output_root,
        sample_document,
        project_root=project_root,
    )
    _validate_residence_determinations(paths.case)
    return RolloutBuildResult(
        judgment_id=document.judgment_id,
        case_sha256=str(result["case_sha256"]),
        retrieval_sha256=str(result["retrieval_sha256"]),
        markdown_sha256=str(result["markdown_sha256"]),
        verbatim_sha256=str(result["verbatim_sha256"]),
        legal_review=_aggregate_legal_review(paths.case),
    )


def execute_rollout_next_batch(
    *,
    manifest_path: Path,
    state_path: Path,
    output_root: Path,
    project_root: Path,
    retry_failed: bool = False,
) -> RolloutExecutionResult:
    return execute_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        executor=lambda document: _build_document(
            document,
            output_root=output_root,
            project_root=project_root,
        ),
        retry_failed=retry_failed,
    )
