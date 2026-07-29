"""Construcción común de un concepto OKF a partir de una sentencia."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from citation_models import ExtractedPage
from citation_source_validation import validate_publishable_fragments
from citation_verification import verify_citation_pages
from okf_annotations import (
    apply_approved_corrections,
    load_annotations,
    validate_annotation_references,
    validate_source_anchors,
)
from okf_models import OkfProvenance
from okf_normalization import normalize_judgment
from okf_provenance import analysis_provenance, extractor_id, sha256_file, write_analysis_snapshot
from okf_rendering import render_judgment_markdown
from okf_verification_report import write_verification_report
from pdf_page_extraction import extract_pdf_pages

PageLoader = Callable[[Path], tuple[str | ExtractedPage, ...]]
GENERATOR_ID = "residenciafiscal-pipeline/0.1.0"


@dataclass(frozen=True)
class DocumentBuild:
    """Artefactos y metadatos de una sentencia ya normalizada y validada."""

    source_file: str
    title: str
    slug: str
    description: str
    document_path: Path
    snapshot_path: Path
    pdf_path: Path
    pdf_sha256: str
    pdf_size_bytes: int
    page_count: int
    extractor: str
    status: str
    literal_count: int
    pending_count: int
    warnings: tuple[str, ...]
    annotation_path: Path | None
    annotation_sha256: str | None
    verification_report_path: Path
    verification_report_sha256: str
    approved_issues: int
    proposed_issues: int
    analysis_provenance: dict[str, object]


def load_unique_record(jsonl_path: Path, source_file: str) -> Mapping[str, object]:
    """Obtiene el único registro del análisis asociado al PDF."""

    matches: list[Mapping[str, object]] = []
    for line_number, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en {jsonl_path}:{line_number}") from exc
        if isinstance(value, dict) and value.get("archivo") == source_file:
            matches.append(value)
    if len(matches) != 1:
        raise ValueError(f"Se esperaba un registro para {source_file}; encontrados: {len(matches)}")
    return matches[0]


def _relative_resource(source_path: Path, destination_dir: Path) -> str:
    return Path(os.path.relpath(source_path.resolve(), destination_dir.resolve())).as_posix()


def build_okf_document(
    *,
    raw_record: Mapping[str, object],
    pdf_path: Path,
    output_dir: Path,
    threshold: float,
    annotations_dir: Path | None = None,
    page_loader: PageLoader = extract_pdf_pages,
) -> DocumentBuild:
    """Genera un concepto sin crear todavía índices ni manifiesto."""

    judgment = normalize_judgment(raw_record)
    annotation_path = (
        annotations_dir / f"{judgment.slug}.yaml" if annotations_dir is not None else None
    )
    annotations = load_annotations(
        annotation_path or Path("__sidecar_disabled__"),
        judgment.archivo,
    )
    validate_annotation_references(judgment, annotations)
    judgment = apply_approved_corrections(judgment, annotations)
    pages = page_loader(pdf_path)
    validate_source_anchors(annotations, pages)
    verifications = tuple(
        verify_citation_pages(
            quote=citation.texto,
            declared_page=citation.pagina,
            pages=pages,
            threshold=threshold,
        )
        for citation in judgment.citas
    )
    validate_publishable_fragments(verifications, pages)
    literal_count = sum(item.publishable_literal for item in verifications)
    pending_count = len(verifications) - literal_count
    status = "draft" if judgment.warnings or pending_count else "stable"

    judgments_dir = output_dir / "sentencias"
    document_path = judgments_dir / f"{judgment.slug}.md"
    snapshot_path = write_analysis_snapshot(output_dir, judgment.slug, raw_record)
    pdf_sha256 = sha256_file(pdf_path)
    provenance = OkfProvenance(
        pdf_resource=_relative_resource(pdf_path, judgments_dir),
        pdf_sha256=pdf_sha256,
        pdf_size_bytes=pdf_path.stat().st_size,
        pdf_page_count=len(pages),
        analysis_source=_relative_resource(snapshot_path, judgments_dir),
        analysis_sha256=sha256_file(snapshot_path),
        generated_by=GENERATOR_ID,
    )
    report_path = write_verification_report(
        output_dir,
        judgment,
        verifications,
        threshold=threshold,
    )
    document = render_judgment_markdown(
        judgment,
        provenance,
        verifications,
        threshold=threshold,
        annotations=annotations,
        verification_report_resource=_relative_resource(report_path, judgments_dir),
    )
    judgments_dir.mkdir(parents=True, exist_ok=True)
    document_path.write_text(document, encoding="utf-8")
    return DocumentBuild(
        source_file=judgment.archivo,
        title=judgment.title,
        slug=judgment.slug,
        description=(
            f"Residencia fiscal; resultado {judgment.resultado_final}; "
            f"criterio decisivo {', '.join(judgment.criterios_decisivos)}."
        ),
        document_path=document_path,
        snapshot_path=snapshot_path,
        pdf_path=pdf_path,
        pdf_sha256=pdf_sha256,
        pdf_size_bytes=pdf_path.stat().st_size,
        page_count=len(pages),
        extractor=extractor_id(),
        status=status,
        literal_count=literal_count,
        pending_count=pending_count,
        warnings=judgment.warnings,
        annotation_path=annotation_path if annotation_path and annotation_path.is_file() else None,
        annotation_sha256=(
            sha256_file(annotation_path)
            if annotation_path is not None and annotation_path.is_file()
            else None
        ),
        verification_report_path=report_path,
        verification_report_sha256=sha256_file(report_path),
        approved_issues=sum(issue.status == "approved" for issue in annotations.issues),
        proposed_issues=sum(issue.status == "proposed" for issue in annotations.issues),
        analysis_provenance=analysis_provenance(raw_record),
    )
