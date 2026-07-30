"""Exporta corpus agregado y evaluación de las 40 preguntas del piloto."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_case_retrieval import load_retrieval_index
from jurisprudence_retrieval_corpus import (
    build_retrieval_corpus,
    render_retrieval_corpus,
)
from jurisprudence_sample_evaluation import (
    evaluate_question_bank,
    parse_question_pilot,
    render_evaluation_bank,
    render_evaluation_report,
)
from jurisprudence_sample_manifest import load_sample_manifest
from okf_provenance import sha256_file


@dataclass(frozen=True)
class SampleEvaluationExportResult:
    artifact_paths: tuple[Path, Path, Path]
    question_count: int
    expected_recall_at_5: float
    expected_recall_at_12: float
    contrast_recall_at_5: float
    contrast_recall_at_12: float
    chat_behavior_gate: str


def _validate_indexes_against_build(
    *,
    manifest_path: Path,
    index_paths: tuple[Path, ...],
    sample_build_path: Path,
) -> None:
    manifest = load_sample_manifest(manifest_path)
    build = json.loads(sample_build_path.read_text(encoding="utf-8"))
    if build.get("manifest_sha256") != sha256_file(manifest_path):
        raise ValueError("sample-build.manifest_sha256 no coincide con el manifiesto")
    if build.get("sample_id") != manifest.sample_id:
        raise ValueError("sample-build.sample_id no coincide con el manifiesto")

    build_documents = {
        item["judgment_id"]: item
        for item in build.get("documents", ())
        if isinstance(item, dict) and "judgment_id" in item
    }
    expected_ids = tuple(item.judgment_id for item in manifest.documents)
    if set(build_documents) != set(expected_ids):
        raise ValueError("sample-build.documents no coincide con el manifiesto")

    for document, index_path in zip(manifest.documents, index_paths, strict=True):
        index = load_retrieval_index(index_path.read_bytes())
        judgment_id = document.judgment_id
        if index.judgment.judgment_id != judgment_id:
            raise ValueError(f"{judgment_id}: judgment_id del índice no coincide")
        unit_judgment_ids = {item.judgment_id for item in index.units}
        if unit_judgment_ids != {judgment_id}:
            raise ValueError(f"{judgment_id}: unit.judgment_id no coincide")
        if index.source.source_sha256 != document.source_sha256:
            raise ValueError(f"{judgment_id}: source_sha256 no coincide")
        if index.source.case_sha256 != build_documents[judgment_id].get("case_sha256"):
            raise ValueError(f"{judgment_id}: case_sha256 no coincide")
        if sha256_file(index_path) != build_documents[judgment_id].get("retrieval_sha256"):
            raise ValueError(f"{judgment_id}: retrieval_sha256 no coincide")


def export_sample_evaluation(
    *,
    manifest_path: Path,
    pilot_path: Path,
    retrieval_root: Path,
    output_root: Path,
    project_root: Path,
    sample_build_path: Path | None = None,
) -> SampleEvaluationExportResult:
    """Construye los tres artefactos desde fuentes versionadas."""

    manifest = load_sample_manifest(manifest_path)
    index_paths = tuple(
        retrieval_root / f"{document.judgment_id}.issues.json" for document in manifest.documents
    )
    _validate_indexes_against_build(
        manifest_path=manifest_path,
        index_paths=index_paths,
        sample_build_path=sample_build_path or retrieval_root.parent / "sample-build.json",
    )
    corpus = build_retrieval_corpus(
        index_paths,
        sample_id=manifest.sample_id,
        project_root=project_root,
    )
    bank = parse_question_pilot(pilot_path)
    if len(bank.questions) != 40:
        raise ValueError(f"el piloto debe contener 40 preguntas: {len(bank.questions)}")
    report = evaluate_question_bank(bank, corpus)
    artifact_paths = (
        output_root / "retrieval/corpus.json",
        output_root / "evaluations/chat-question-pilot-5.bank.json",
        output_root / "reports/chat-question-pilot-5.retrieval-evaluation.json",
    )
    payloads = (
        render_retrieval_corpus(corpus),
        render_evaluation_bank(bank),
        render_evaluation_report(report),
    )
    for payload, path in zip(payloads, artifact_paths, strict=True):
        write_case_derivative(payload, path)
    return SampleEvaluationExportResult(
        artifact_paths=artifact_paths,
        question_count=report.question_count,
        expected_recall_at_5=report.expected_recall_at_5,
        expected_recall_at_12=report.expected_recall_at_12,
        contrast_recall_at_5=report.contrast_recall_at_5,
        contrast_recall_at_12=report.contrast_recall_at_12,
        chat_behavior_gate=report.chat_behavior_gate,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evalúa las 40 preguntas contra la muestra v3.",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--retrieval-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--sample-build", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = export_sample_evaluation(
        manifest_path=args.manifest,
        pilot_path=args.pilot,
        retrieval_root=args.retrieval_root,
        output_root=args.output_root,
        project_root=args.project_root,
        sample_build_path=args.sample_build,
    )
    print(
        json.dumps(
            {
                "artifacts": tuple(str(item) for item in result.artifact_paths),
                "contrast_recall_at_5": result.contrast_recall_at_5,
                "contrast_recall_at_12": result.contrast_recall_at_12,
                "expected_recall_at_5": result.expected_recall_at_5,
                "expected_recall_at_12": result.expected_recall_at_12,
                "question_count": result.question_count,
                "artifact_validation": "passed",
                "chat_behavior_gate": result.chat_behavior_gate,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
