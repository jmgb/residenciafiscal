"""Índices y manifiesto deterministas para un lote OKF."""

from __future__ import annotations

import os
from pathlib import Path

from okf_document_builder import DocumentBuild
from okf_provenance import sha256_file


def _relative(path: Path, output_dir: Path) -> str:
    return Path(os.path.relpath(path.resolve(), output_dir.resolve())).as_posix()


def render_judgments_index_many(builds: tuple[DocumentBuild, ...]) -> str:
    """Lista conceptos en el mismo orden estable que el manifiesto."""

    entries = "".join(
        f"* [{build.title}]({build.slug}.md) - {build.description}\n" for build in builds
    )
    return f"# Sentencias sobre residencia fiscal\n\n{entries}"


def _analysis_record(build: DocumentBuild, output_dir: Path) -> dict[str, object]:
    return {
        "archivo": build.source_file,
        "path": build.snapshot_path.relative_to(output_dir).as_posix(),
        "sha256": sha256_file(build.snapshot_path),
        "provenance": build.analysis_provenance,
    }


def _annotation_source(
    build: DocumentBuild,
    output_dir: Path,
) -> dict[str, object] | None:
    if build.annotation_path is None:
        return None
    return {
        "archivo": build.source_file,
        "path": _relative(build.annotation_path, output_dir),
        "sha256": build.annotation_sha256,
    }


def _pdf_source(build: DocumentBuild) -> dict[str, object]:
    return {
        "archivo": build.source_file,
        "sha256": build.pdf_sha256,
        "size_bytes": build.pdf_size_bytes,
        "pages": build.page_count,
        "extractor": build.extractor,
    }


def _document(build: DocumentBuild, output_dir: Path) -> dict[str, object]:
    relative_path = build.document_path.relative_to(output_dir)
    return {
        "concept_id": f"sentencias/{build.slug}",
        "path": relative_path.as_posix(),
        "sha256": sha256_file(build.document_path),
        "status": build.status,
        "literal_citations": build.literal_count,
        "pending_citations": build.pending_count,
        "legal_issues": {
            "approved": build.approved_issues,
            "proposed": build.proposed_issues,
        },
        "verification_report": {
            "path": build.verification_report_path.relative_to(output_dir).as_posix(),
            "sha256": build.verification_report_sha256,
        },
        "normalization_warnings": list(build.warnings),
    }


def build_batch_manifest(
    *,
    jsonl_path: Path,
    output_dir: Path,
    builds: tuple[DocumentBuild, ...],
) -> dict[str, object]:
    """Construye el manifiesto v3 sin marcas temporales."""

    annotation_sources = tuple(
        source for build in builds if (source := _annotation_source(build, output_dir)) is not None
    )
    return {
        "schema_version": "residenciafiscal-okf-manifest/3",
        "okf_version": "0.2",
        "scope": {
            "documents": len(builds),
            "source_files": [build.source_file for build in builds],
        },
        "analysis_source": {
            "path": jsonl_path.as_posix(),
            "sha256": sha256_file(jsonl_path),
        },
        "analysis_records": [_analysis_record(build, output_dir) for build in builds],
        "annotations_sources": list(annotation_sources),
        "pdf_sources": [_pdf_source(build) for build in builds],
        "documents": [_document(build, output_dir) for build in builds],
    }
