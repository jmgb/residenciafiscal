#!/usr/bin/env python3
"""Ejecuta el spike determinista de verificación sobre ``frases_clave``."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from citation_report import finding_to_dict, render_markdown_report, summarize_findings
from citation_sample_manifest import load_sample_manifest
from citation_spike import (
    PageLoader,
    extract_citation_candidates,
    extract_pdf_pages,
    load_citation_sources,
    select_candidates_by_source_order,
    verify_loaded_citations,
)

DEFAULT_THRESHOLDS = "70,75,80,85,90,95"


def parse_thresholds(raw_thresholds: str) -> tuple[float, ...]:
    """Parsea una lista de puntuaciones RapidFuzz entre 0 y 100."""

    if not raw_thresholds.strip():
        raise ValueError("La lista de umbrales no puede estar vacía")
    try:
        thresholds = {float(value.strip()) for value in raw_thresholds.split(",")}
    except ValueError as exc:
        raise ValueError("Los umbrales deben ser números separados por comas") from exc
    if not thresholds or any(threshold <= 0 or threshold > 100 for threshold in thresholds):
        raise ValueError("Cada umbral debe estar en el intervalo (0, 100]")
    return tuple(sorted(thresholds))


def _load_jsonl(jsonl_path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en {jsonl_path}:{line_number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Se esperaba un objeto JSON en {jsonl_path}:{line_number}")
        records.append(record)
    return records


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verifica frases_clave del JSONL contra sus PDF, sin llamadas LLM."
    )
    parser.add_argument("--jsonl", type=Path, required=True, help="JSONL de análisis")
    parser.add_argument("--pdf-dir", type=Path, default=Path("sentencias"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/citation-verification"))
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        "--source-file",
        help="Limita el spike al nombre exacto de un PDF presente en el JSONL",
    )
    scope_group.add_argument(
        "--manifest",
        type=Path,
        help="Manifiesto JSON con una muestra ordenada de sentencias",
    )
    parser.add_argument("--threshold", type=float, default=85.0)
    parser.add_argument(
        "--thresholds",
        default=DEFAULT_THRESHOLDS,
        help=f"Umbrales para sensibilidad (por defecto: {DEFAULT_THRESHOLDS})",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    page_loader: PageLoader = extract_pdf_pages,
) -> int:
    """Ejecuta el spike y escribe un JSON detallado y un resumen Markdown."""

    args = _build_parser().parse_args(argv)
    if not args.jsonl.is_file():
        raise FileNotFoundError(f"JSONL no encontrado: {args.jsonl}")
    thresholds = set(parse_thresholds(args.thresholds))
    if args.threshold <= 0 or args.threshold > 100:
        raise ValueError("El umbral seleccionado debe estar en el intervalo (0, 100]")
    thresholds.add(float(args.threshold))

    records = _load_jsonl(args.jsonl)
    candidates = extract_citation_candidates(records)
    source_files: tuple[str, ...] = ()
    manifest = None
    if args.source_file:
        source_files = (args.source_file,)
    elif args.manifest:
        manifest = load_sample_manifest(args.manifest)
        source_files = manifest.source_files
    if source_files:
        candidates = select_candidates_by_source_order(candidates, source_files)
    loaded = load_citation_sources(candidates, args.pdf_dir, page_loader=page_loader)

    findings_by_threshold = {
        threshold: verify_loaded_citations(loaded, threshold=threshold)
        for threshold in sorted(thresholds)
    }
    threshold_summaries = {
        threshold: summarize_findings(findings)
        for threshold, findings in findings_by_threshold.items()
    }
    selected_findings = findings_by_threshold[float(args.threshold)]
    selected_summary = threshold_summaries[float(args.threshold)]

    report = {
        "config": {
            "source_jsonl": str(args.jsonl),
            "source_jsonl_sha256": _sha256(args.jsonl),
            "pdf_dir": str(args.pdf_dir),
            "source_file": args.source_file,
            "manifest": str(args.manifest) if args.manifest else None,
            "manifest_name": manifest.name if manifest else None,
            "source_files": list(source_files),
            "threshold": args.threshold,
            "thresholds": sorted(thresholds),
            "records": len(records),
            "candidates": len(candidates),
        },
        "summary": selected_summary,
        "threshold_summaries": {
            f"{threshold:g}": summary for threshold, summary in threshold_summaries.items()
        },
        "findings": [finding_to_dict(finding) for finding in selected_findings],
    }
    markdown = render_markdown_report(
        summary=selected_summary,
        threshold=args.threshold,
        source_jsonl=str(args.jsonl),
        threshold_summaries=threshold_summaries,
        source_files=source_files,
        findings=selected_findings,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "citation-verification.json"
    markdown_path = args.output_dir / "citation-verification.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(markdown, encoding="utf-8")

    print(
        f"Localizadas {selected_summary['located_citations']}/"
        f"{selected_summary['total_citations']} citas "
        f"({selected_summary['literal_citations']} literales; "
        f"umbral {args.threshold:g})."
    )
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
