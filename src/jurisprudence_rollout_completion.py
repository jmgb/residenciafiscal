"""Cierre agregado y auditable de un rollout jurisprudencial."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_retrieval_corpus import build_retrieval_corpus, render_retrieval_corpus
from jurisprudence_rollout import load_rollout_manifest, load_rollout_state
from jurisprudence_rollout_models import RolloutExecutionStatus, RolloutState
from jurisprudence_sample_quality import (
    build_sample_quality_report,
    render_sample_quality_report,
)
from okf_provenance import sha256_file

PublicationStatus = Literal["HUMAN_APPROVED", "AGENT_REVIEWED_ONLY"]


@dataclass(frozen=True)
class RolloutCompletionResult:
    document_count: int
    retrieval_document_count: int
    publication_status: PublicationStatus
    build_path: Path


def _render(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def rollout_corpus_path(output_root: Path, document_count: int) -> Path:
    """Separa el agregado del rollout del corpus piloto consumido por el chat."""

    return output_root / f"retrieval/rollout-{document_count}.corpus.json"


def _validate_artifact_hashes(state: RolloutState, output_root: Path) -> None:
    resources = {
        "case_sha256": "cases/{judgment_id}.case.json",
        "retrieval_sha256": "retrieval/{judgment_id}.issues.json",
        "markdown_sha256": "perfiles/{judgment_id}.md",
        "verbatim_sha256": "verbatim/{judgment_id}.pages.json",
    }
    for document in state.documents:
        for field_name, template in resources.items():
            expected = getattr(document, field_name)
            path = output_root / template.format(judgment_id=document.judgment_id)
            if expected is None or not path.is_file() or sha256_file(path) != expected:
                raise ValueError(f"{document.judgment_id}.{field_name} no coincide con el estado")


def finalize_rollout(
    *,
    manifest_path: Path,
    state_path: Path,
    output_root: Path,
    project_root: Path,
) -> RolloutCompletionResult:
    """Agrega únicamente cuando todos los documentos superan el build técnico."""

    manifest = load_rollout_manifest(manifest_path)
    state = load_rollout_state(state_path)
    if state.manifest_sha256 != sha256_file(manifest_path):
        raise ValueError("el estado no corresponde al manifiesto")
    incomplete = tuple(
        item.judgment_id
        for item in state.documents
        if item.execution_status != RolloutExecutionStatus.BUILD_PASSED
    )
    if incomplete:
        raise ValueError(f"todos los documentos deben estar BUILD_PASSED: {incomplete}")
    _validate_artifact_hashes(state, output_root)
    index_paths = tuple(
        output_root / f"retrieval/{item.judgment_id}.issues.json" for item in manifest.documents
    )
    case_paths = tuple(
        output_root / f"cases/{item.judgment_id}.case.json" for item in manifest.documents
    )
    corpus = build_retrieval_corpus(
        index_paths,
        sample_id=manifest.rollout_id,
        project_root=project_root,
    )
    quality = build_sample_quality_report(
        case_paths,
        sample_id=manifest.rollout_id,
        project_root=project_root,
    )
    retrieval_documents = len({unit.judgment_id for unit in corpus.units})
    human_approved = sum(item.legal_review == "HUMAN_APPROVED" for item in state.documents)
    publication_status: PublicationStatus = (
        "HUMAN_APPROVED" if human_approved == len(state.documents) else "AGENT_REVIEWED_ONLY"
    )
    corpus_path = rollout_corpus_path(output_root, len(state.documents))
    quality_path = output_root / f"reports/rollout-{len(state.documents)}.quality.json"
    build_path = output_root / "rollout-build.json"
    write_case_derivative(render_retrieval_corpus(corpus), corpus_path)
    write_case_derivative(render_sample_quality_report(quality), quality_path)
    write_case_derivative(
        _render(
            {
                "schema_version": "residenciafiscal-rollout-build/1",
                "rollout_id": manifest.rollout_id,
                "manifest_sha256": sha256_file(manifest_path),
                "state_sha256": sha256_file(state_path),
                "document_count": len(state.documents),
                "retrieval_document_count": retrieval_documents,
                "retrieval_unit_count": len(corpus.units),
                "human_approved_documents": human_approved,
                "publication_status": publication_status,
                "corpus_sha256": sha256_file(corpus_path),
                "quality_sha256": sha256_file(quality_path),
            }
        ),
        build_path,
    )
    return RolloutCompletionResult(
        document_count=len(state.documents),
        retrieval_document_count=retrieval_documents,
        publication_status=publication_status,
        build_path=build_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cierra y agrega un rollout jurisprudencial.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = finalize_rollout(
        manifest_path=args.manifest,
        state_path=args.state,
        output_root=args.output_root,
        project_root=args.project_root,
    )
    print(
        _render(
            {
                "documents": result.document_count,
                "retrieval_documents": result.retrieval_document_count,
                "publication_status": result.publication_status,
                "build": str(result.build_path),
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
