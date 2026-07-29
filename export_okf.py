#!/usr/bin/env python3
"""Exporta una sentencia analizada como bundle jurídico OKF v0.2."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from okf_bundle import PageLoader, build_okf_bundle
from pdf_page_extraction import extract_pdf_pages


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera y valida un bundle OKF para una sentencia, sin llamadas LLM."
    )
    parser.add_argument("--jsonl", type=Path, required=True, help="JSONL de análisis")
    parser.add_argument("--pdf-dir", type=Path, default=Path("sentencias"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("knowledge/jurisprudencia"),
    )
    parser.add_argument(
        "--source-file",
        required=True,
        help="Nombre exacto del único PDF que se exportará",
    )
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=None,
        help="Sidecars de revisión; son opcionales y nunca alteran texto legal",
    )
    parser.add_argument("--threshold", type=float, default=85.0)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    page_loader: PageLoader = extract_pdf_pages,
) -> int:
    """Ejecuta el ciclo de exportación y muestra sus artefactos principales."""

    args = _build_parser().parse_args(argv)
    if args.threshold <= 0 or args.threshold > 100:
        raise ValueError("El umbral debe estar en el intervalo (0, 100]")
    result = build_okf_bundle(
        jsonl_path=args.jsonl,
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
        source_file=args.source_file,
        threshold=args.threshold,
        annotations_dir=args.annotations_dir,
        page_loader=page_loader,
    )
    print(
        f"OKF generado: {result.document_count} sentencia, "
        f"{result.literal_citation_count} citas literales y "
        f"{result.pending_citation_count} pendientes."
    )
    print(f"Documento: {result.document_path}")
    print(f"Manifiesto: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
