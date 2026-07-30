"""Orquestador reentrante del pipeline híbrido para una muestra v3."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from export_jurisprudence_case import export_jurisprudence_case
from export_jurisprudence_case_derivatives import export_case_derivatives
from export_verbatim import export_verbatim_document
from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_sample_manifest import (
    JurisprudenceSampleDocument,
    load_sample_manifest,
    validate_sample_inputs,
)
from okf_provenance import sha256_file


@dataclass(frozen=True)
class SampleDocumentPaths:
    verbatim: Path
    case: Path
    evaluation: Path
    markdown: Path
    retrieval: Path
    case_report: Path
    derivatives_report: Path


@dataclass(frozen=True)
class SampleExportResult:
    sample_id: str
    document_ids: tuple[str, ...]
    report_path: Path


def sample_document_paths(
    output_root: Path,
    document: JurisprudenceSampleDocument,
    *,
    project_root: Path,
) -> SampleDocumentPaths:
    """Resuelve todos los destinos canónicos de un documento."""

    judgment_id = document.judgment_id
    return SampleDocumentPaths(
        verbatim=output_root / f"verbatim/{judgment_id}.pages.json",
        case=output_root / f"cases/{judgment_id}.case.json",
        evaluation=(project_root / document.evaluation_path).resolve(),
        markdown=output_root / f"perfiles/{judgment_id}.md",
        retrieval=output_root / f"retrieval/{judgment_id}.issues.json",
        case_report=output_root / f"reports/{judgment_id}.case-validation.json",
        derivatives_report=(output_root / f"reports/{judgment_id}.derivatives-validation.json"),
    )


def export_jurisprudence_document(
    document: JurisprudenceSampleDocument,
    *,
    output_root: Path,
    project_root: Path,
) -> dict[str, object]:
    paths = sample_document_paths(
        output_root,
        document,
        project_root=project_root,
    )
    export_verbatim_document(
        pdf_path=project_root / document.source_file,
        document_id=document.judgment_id,
        source_file=document.source_file,
        output_path=paths.verbatim,
        project_root=project_root,
    )
    export_jurisprudence_case(
        proposal_path=project_root / document.proposal_path,
        verbatim_path=paths.verbatim,
        evaluation_path=paths.evaluation,
        output_path=paths.case,
        report_path=paths.case_report,
        project_root=project_root,
    )
    export_case_derivatives(
        case_path=paths.case,
        verbatim_path=paths.verbatim,
        markdown_path=paths.markdown,
        retrieval_path=paths.retrieval,
        report_path=paths.derivatives_report,
        project_root=project_root,
    )
    case = load_jurisprudence_case(paths.case.read_bytes())
    return {
        "case_sha256": sha256_file(paths.case),
        "derivatives_report_sha256": sha256_file(paths.derivatives_report),
        "judgment_id": document.judgment_id,
        "legal_issue_count": len(case.legal_issues),
        "markdown_sha256": sha256_file(paths.markdown),
        "retrieval_sha256": sha256_file(paths.retrieval),
        "verbatim_sha256": sha256_file(paths.verbatim),
    }


def _selected_documents(
    documents: tuple[JurisprudenceSampleDocument, ...],
    only_judgment_ids: tuple[str, ...] | None,
) -> tuple[JurisprudenceSampleDocument, ...]:
    if only_judgment_ids is None:
        return documents
    available = {item.judgment_id for item in documents}
    missing = set(only_judgment_ids) - available
    if missing:
        raise ValueError(f"judgment_id ausente del manifiesto: {sorted(missing)}")
    selected = set(only_judgment_ids)
    return tuple(item for item in documents if item.judgment_id in selected)


def export_jurisprudence_sample(
    *,
    manifest_path: Path,
    output_root: Path,
    project_root: Path,
    only_judgment_ids: tuple[str, ...] | None = None,
) -> SampleExportResult:
    """Ejecuta el mismo pipeline para cada documento seleccionado."""

    manifest = load_sample_manifest(manifest_path)
    validate_sample_inputs(manifest, project_root=project_root)
    documents = _selected_documents(manifest.documents, only_judgment_ids)
    results = tuple(
        export_jurisprudence_document(
            document,
            output_root=output_root,
            project_root=project_root,
        )
        for document in documents
    )
    report_path = output_root / "sample-build.json"
    report = (
        json.dumps(
            {
                "documents": results,
                "manifest_sha256": sha256_file(manifest_path),
                "sample_id": manifest.sample_id,
                "schema_version": "residenciafiscal-jurisprudence-sample-build/1",
                "validation": "passed",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    write_case_derivative(report, report_path)
    return SampleExportResult(
        sample_id=manifest.sample_id,
        document_ids=tuple(item.judgment_id for item in documents),
        report_path=report_path,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenera una muestra jurisprudencial v3 por manifiesto.",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--only", action="append", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = export_jurisprudence_sample(
        manifest_path=args.manifest,
        output_root=args.output_root,
        project_root=args.project_root,
        only_judgment_ids=tuple(args.only) if args.only else None,
    )
    print(
        json.dumps(
            {
                "documents": result.document_ids,
                "report": str(result.report_path),
                "sample_id": result.sample_id,
                "validation": "passed",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
