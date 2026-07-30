"""Construcción atómica de un bundle OKF para una muestra explícita."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterable
from pathlib import Path

from okf_batch_artifacts import build_batch_manifest, render_judgments_index_many
from okf_bundle import BundleBuildResult
from okf_bundle_artifacts import render_root_index
from okf_document_builder import (
    DocumentBuild,
    PageLoader,
    build_okf_document,
    load_unique_record,
)
from okf_validation import validate_okf_bundle
from pdf_page_extraction import extract_pdf_pages


def _validate_inputs(
    jsonl_path: Path,
    pdf_dir: Path,
    output_dir: Path,
    source_files: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[dict[str, object], ...]]:
    if output_dir.exists():
        raise FileExistsError(f"El destino ya existe: {output_dir}")
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"JSONL no encontrado: {jsonl_path}")
    if not source_files:
        raise ValueError("La selección de sentencias está vacía")
    if len(source_files) != len(set(source_files)):
        raise ValueError("La selección contiene PDFs duplicados")
    ordered = tuple(sorted(source_files))
    records: list[dict[str, object]] = []
    for source_file in ordered:
        pdf_path = pdf_dir / source_file
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        records.append(dict(load_unique_record(jsonl_path, source_file)))
    return ordered, tuple(records)


def _write_batch_artifacts(
    *,
    jsonl_path: Path,
    output_dir: Path,
    builds: tuple[DocumentBuild, ...],
) -> Path:
    (output_dir / "index.md").write_text(render_root_index(), encoding="utf-8")
    judgments_dir = output_dir / "sentencias"
    (judgments_dir / "index.md").write_text(
        render_judgments_index_many(builds),
        encoding="utf-8",
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            build_batch_manifest(
                jsonl_path=jsonl_path,
                output_dir=output_dir,
                builds=builds,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_okf_batch(
    *,
    jsonl_path: Path,
    pdf_dir: Path,
    output_dir: Path,
    source_files: Iterable[str],
    threshold: float,
    annotations_dir: Path | None = None,
    page_loader: PageLoader = extract_pdf_pages,
) -> BundleBuildResult:
    """Construye una muestra y la publica solo después de validarla."""

    ordered, records = _validate_inputs(
        jsonl_path,
        pdf_dir,
        output_dir,
        tuple(source_files),
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}-",
        dir=output_dir.parent,
    ) as temporary:
        staging_dir = Path(temporary)
        builds = tuple(
            build_okf_document(
                raw_record=record,
                pdf_path=pdf_dir / source_file,
                output_dir=staging_dir,
                threshold=threshold,
                annotations_dir=annotations_dir,
                page_loader=page_loader,
            )
            for source_file, record in zip(ordered, records, strict=True)
        )
        manifest_path = _write_batch_artifacts(
            jsonl_path=jsonl_path,
            output_dir=staging_dir,
            builds=builds,
        )
        issues = validate_okf_bundle(staging_dir)
        if issues:
            raise ValueError("Bundle OKF inválido: " + "; ".join(issues))
        staging_dir.rename(output_dir)

    return BundleBuildResult(
        document_path=output_dir / "sentencias",
        manifest_path=output_dir / manifest_path.name,
        document_count=len(builds),
        literal_citation_count=sum(build.literal_count for build in builds),
        pending_citation_count=sum(build.pending_count for build in builds),
    )
