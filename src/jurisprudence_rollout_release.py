"""Verificación de integridad y tamaño de un rollout ya materializado."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jurisprudence_retrieval_corpus import load_retrieval_corpus
from jurisprudence_rollout import load_rollout_manifest, load_rollout_state
from jurisprudence_rollout_models import RolloutExecutionStatus
from okf_provenance import sha256_file

MAX_ARTIFACT_FILES = 1_000
MAX_ARTIFACT_BYTES = 50_000_000


@dataclass(frozen=True)
class RolloutReleaseVerification:
    document_count: int
    retrieval_document_count: int
    retrieval_unit_count: int
    publication_status: str
    artifact_file_count: int
    artifact_bytes: int


def _require_hash(path: Path, expected: str | None, label: str) -> None:
    if expected is None or not path.is_file() or sha256_file(path) != expected:
        raise ValueError(f"hash no coincide: {label}")


def verify_rollout_release(
    *, manifest_path: Path, output_root: Path, project_root: Path
) -> RolloutReleaseVerification:
    """Verifica procedencia, derivados agregados y presupuesto del repositorio."""

    manifest = load_rollout_manifest(manifest_path)
    state_path = project_root / "output/jurisprudence-v3-rollout-state.json"
    build_path = output_root / "rollout-build.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    state = load_rollout_state(state_path)

    _require_hash(manifest_path, build.get("manifest_sha256"), "manifest")
    _require_hash(state_path, build.get("state_sha256"), "state")
    if state.manifest_sha256 != sha256_file(manifest_path):
        raise ValueError("el estado no corresponde al manifiesto")
    if any(
        document.execution_status != RolloutExecutionStatus.BUILD_PASSED
        for document in state.documents
    ):
        raise ValueError("el estado contiene documentos sin BUILD_PASSED")

    state_by_id = {item.judgment_id: item for item in state.documents}
    artifact_templates = {
        "case_sha256": "cases/{judgment_id}.case.json",
        "retrieval_sha256": "retrieval/{judgment_id}.issues.json",
        "markdown_sha256": "perfiles/{judgment_id}.md",
        "verbatim_sha256": "verbatim/{judgment_id}.pages.json",
    }
    for document in manifest.documents:
        _require_hash(
            project_root / document.source_file,
            document.source_sha256,
            f"{document.judgment_id}.source",
        )
        _require_hash(
            project_root / document.proposal_path,
            document.proposal_sha256,
            f"{document.judgment_id}.proposal",
        )
        _require_hash(
            project_root / document.evaluation_path,
            document.evaluation_sha256,
            f"{document.judgment_id}.evaluation",
        )
        state_document = state_by_id[document.judgment_id]
        for field_name, template in artifact_templates.items():
            _require_hash(
                output_root / template.format(judgment_id=document.judgment_id),
                getattr(state_document, field_name),
                f"{document.judgment_id}.{field_name}",
            )

    document_count = len(manifest.documents)
    corpus_path = output_root / f"retrieval/rollout-{document_count}.corpus.json"
    quality_path = output_root / f"reports/rollout-{document_count}.quality.json"
    _require_hash(corpus_path, build.get("corpus_sha256"), "aggregate corpus")
    _require_hash(quality_path, build.get("quality_sha256"), "quality report")
    corpus = load_retrieval_corpus(corpus_path.read_bytes())
    manifest_ids = {item.judgment_id for item in manifest.documents}
    if {item.judgment_id for item in corpus.sources} != manifest_ids:
        raise ValueError("las fuentes del corpus no coinciden con el manifiesto")
    for source in corpus.sources:
        _require_hash(
            project_root / source.index_resource,
            source.index_sha256,
            f"{source.judgment_id}.corpus-index",
        )

    files = tuple(path for path in output_root.rglob("*") if path.is_file())
    artifact_bytes = sum(path.stat().st_size for path in files)
    if len(files) >= MAX_ARTIFACT_FILES or artifact_bytes >= MAX_ARTIFACT_BYTES:
        raise ValueError("el rollout excede el presupuesto de artefactos versionados")
    expected = {
        "document_count": document_count,
        "retrieval_document_count": len({unit.judgment_id for unit in corpus.units}),
        "retrieval_unit_count": len(corpus.units),
    }
    for field_name, value in expected.items():
        if build.get(field_name) != value:
            raise ValueError(f"{field_name} no coincide con el build")
    return RolloutReleaseVerification(
        **expected,
        publication_status=build["publication_status"],
        artifact_file_count=len(files),
        artifact_bytes=artifact_bytes,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica el release jurisprudencial.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = verify_rollout_release(
        manifest_path=args.manifest,
        output_root=args.output_root,
        project_root=args.project_root,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
