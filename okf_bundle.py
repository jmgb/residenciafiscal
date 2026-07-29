"""Construcción reproducible de un bundle OKF para una sentencia."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from okf_bundle_artifacts import (
    build_manifest,
    render_judgments_index,
    render_root_index,
)
from okf_document_builder import (
    PageLoader,
    build_okf_document,
    load_unique_record,
)
from okf_provenance import sha256_file
from okf_validation import validate_okf_bundle
from pdf_page_extraction import extract_pdf_pages


@dataclass(frozen=True)
class BundleBuildResult:
    """Rutas y métricas estables de una construcción OKF."""

    document_path: Path
    manifest_path: Path
    document_count: int
    literal_citation_count: int
    pending_citation_count: int


def build_okf_bundle(
    *,
    jsonl_path: Path,
    pdf_dir: Path,
    output_dir: Path,
    source_file: str,
    threshold: float,
    annotations_dir: Path | None = None,
    page_loader: PageLoader = extract_pdf_pages,
) -> BundleBuildResult:
    """Ejecuta JSONL → normalización → citas → OKF → validación para un PDF."""

    if not jsonl_path.is_file():
        raise FileNotFoundError(f"JSONL no encontrado: {jsonl_path}")
    pdf_path = pdf_dir / source_file
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    raw_record = load_unique_record(jsonl_path, source_file)
    build = build_okf_document(
        raw_record=raw_record,
        pdf_path=pdf_path,
        output_dir=output_dir,
        threshold=threshold,
        annotations_dir=annotations_dir,
        page_loader=page_loader,
    )
    judgments_dir = output_dir / "sentencias"
    document_path = build.document_path
    judgments_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.md").write_text(render_root_index(), encoding="utf-8")
    (judgments_dir / "index.md").write_text(
        render_judgments_index(build.title, build.slug, build.description),
        encoding="utf-8",
    )

    relative_document = document_path.relative_to(output_dir)
    manifest = build_manifest(
        jsonl_path=jsonl_path,
        analysis_sha256=sha256_file(jsonl_path),
        analysis_provenance=build.analysis_provenance,
        source_record_path=build.snapshot_path.relative_to(output_dir),
        source_record_sha256=sha256_file(build.snapshot_path),
        pdf_path=pdf_path,
        pdf_sha256=build.pdf_sha256,
        extractor=build.extractor,
        page_count=build.page_count,
        document_path=relative_document,
        document_sha256=sha256_file(document_path),
        status=build.status,
        literal_count=build.literal_count,
        pending_count=build.pending_count,
        warnings=build.warnings,
        annotation_path=(
            Path(os.path.relpath(build.annotation_path.resolve(), output_dir.resolve()))
            if build.annotation_path
            else None
        ),
        annotation_sha256=build.annotation_sha256,
        approved_issues=build.approved_issues,
        proposed_issues=build.proposed_issues,
        verification_report_path=build.verification_report_path.relative_to(output_dir),
        verification_report_sha256=build.verification_report_sha256,
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    issues = validate_okf_bundle(output_dir)
    if issues:
        raise ValueError("Bundle OKF inválido: " + "; ".join(issues))
    return BundleBuildResult(
        document_path=document_path,
        manifest_path=manifest_path,
        document_count=1,
        literal_citation_count=build.literal_count,
        pending_citation_count=build.pending_count,
    )
