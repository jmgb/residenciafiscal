"""Construcción reproducible de un bundle OKF jurisprudencial acotado."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from citation_models import ExtractedPage
from citation_verification import verify_citation_pages
from okf_bundle_artifacts import (
    build_manifest,
    render_judgments_index,
    render_root_index,
)
from okf_models import OkfProvenance
from okf_normalization import normalize_judgment
from okf_rendering import render_judgment_markdown
from okf_validation import validate_okf_bundle
from pdf_page_extraction import extract_pdf_pages

PageLoader = Callable[[Path], tuple[str | ExtractedPage, ...]]
GENERATOR_ID = "residenciafiscal-pipeline/0.1.0"


@dataclass(frozen=True)
class BundleBuildResult:
    """Rutas y métricas estables de una construcción OKF."""

    document_path: Path
    manifest_path: Path
    document_count: int
    literal_citation_count: int
    pending_citation_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _load_unique_record(jsonl_path: Path, source_file: str) -> Mapping[str, object]:
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


def _relative_resource(source_path: Path, concept_dir: Path) -> str:
    return Path(os.path.relpath(source_path.resolve(), concept_dir.resolve())).as_posix()


def build_okf_bundle(
    *,
    jsonl_path: Path,
    pdf_dir: Path,
    output_dir: Path,
    source_file: str,
    threshold: float,
    page_loader: PageLoader = extract_pdf_pages,
) -> BundleBuildResult:
    """Ejecuta JSONL → normalización → citas → OKF → validación para un PDF."""

    if not jsonl_path.is_file():
        raise FileNotFoundError(f"JSONL no encontrado: {jsonl_path}")
    pdf_path = pdf_dir / source_file
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    judgment = normalize_judgment(_load_unique_record(jsonl_path, source_file))
    pages = page_loader(pdf_path)
    verifications = tuple(
        verify_citation_pages(
            quote=citation.texto,
            declared_page=citation.pagina,
            pages=pages,
            threshold=threshold,
        )
        for citation in judgment.citas
    )
    literal_count = sum(verification.literal for verification in verifications)
    pending_count = len(verifications) - literal_count
    status = "draft" if judgment.warnings or pending_count else "stable"

    judgments_dir = output_dir / "sentencias"
    document_path = judgments_dir / f"{judgment.slug}.md"
    provenance = OkfProvenance(
        pdf_resource=_relative_resource(pdf_path, judgments_dir),
        pdf_sha256=_sha256(pdf_path),
        pdf_size_bytes=pdf_path.stat().st_size,
        pdf_page_count=len(pages),
        analysis_source=_relative_resource(jsonl_path, judgments_dir),
        analysis_sha256=_sha256(jsonl_path),
        generated_by=GENERATOR_ID,
    )
    document = render_judgment_markdown(
        judgment,
        provenance,
        verifications,
        threshold=threshold,
    )
    description = (
        f"Residencia fiscal; resultado {judgment.resultado_final}; "
        f"criterio decisivo {', '.join(judgment.criterios_decisivos)}."
    )
    judgments_dir.mkdir(parents=True, exist_ok=True)
    document_path.write_text(document, encoding="utf-8")
    (output_dir / "index.md").write_text(render_root_index(), encoding="utf-8")
    (judgments_dir / "index.md").write_text(
        render_judgments_index(judgment.title, judgment.slug, description),
        encoding="utf-8",
    )

    relative_document = document_path.relative_to(output_dir)
    manifest = build_manifest(
        jsonl_path=jsonl_path,
        analysis_sha256=provenance.analysis_sha256,
        pdf_path=pdf_path,
        pdf_sha256=provenance.pdf_sha256,
        page_count=len(pages),
        document_path=relative_document,
        document_sha256=_sha256(document_path),
        status=status,
        literal_count=literal_count,
        pending_count=pending_count,
        warnings=judgment.warnings,
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
        literal_citation_count=literal_count,
        pending_citation_count=pending_count,
    )
