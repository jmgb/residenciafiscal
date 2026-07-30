#!/usr/bin/env python3
"""Exporta una muestra congelada como bundle jurídico OKF v0.2."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from okf_batch import build_okf_batch
from okf_batch_manifest import load_okf_batch_manifest, validate_batch_sources
from okf_document_builder import PageLoader
from pdf_page_extraction import extract_pdf_pages


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un bundle OKF desde un manifiesto explícito, sin llamadas LLM."
    )
    parser.add_argument("--jsonl", type=Path, required=True, help="JSONL de análisis")
    parser.add_argument("--manifest", type=Path, required=True, help="Selección OKF congelada")
    parser.add_argument("--pdf-dir", type=Path, default=Path("sentencias"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("knowledge/jurisprudencia-muestra-5"),
    )
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=None,
        help="Sidecars generados por revisión jurídica asistida",
    )
    parser.add_argument("--threshold", type=float, default=85.0)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    page_loader: PageLoader = extract_pdf_pages,
) -> int:
    """Valida el manifiesto y publica el lote de forma atómica."""

    args = _build_parser().parse_args(argv)
    if args.threshold <= 0 or args.threshold > 100:
        raise ValueError("El umbral debe estar en el intervalo (0, 100]")
    manifest = load_okf_batch_manifest(args.manifest)
    source_files = validate_batch_sources(manifest, args.jsonl, args.pdf_dir)
    result = build_okf_batch(
        jsonl_path=args.jsonl,
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
        source_files=source_files,
        threshold=args.threshold,
        annotations_dir=args.annotations_dir,
        page_loader=page_loader,
    )
    print(
        f"OKF generado: {result.document_count} sentencias, "
        f"{result.literal_citation_count} citas literales y "
        f"{result.pending_citation_count} pendientes."
    )
    print(f"Directorio: {result.document_path}")
    print(f"Manifiesto: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
