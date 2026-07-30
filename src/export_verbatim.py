"""CLI para generar y validar un artefacto verbatim sin LLM."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path

from verbatim_artifact import write_verbatim_corpus
from verbatim_extraction import extract_verbatim_corpus
from verbatim_validation import (
    VerbatimValidationResult,
    validate_verbatim_artifact,
)


def export_verbatim_document(
    *,
    pdf_path: Path,
    document_id: str,
    source_file: str,
    output_path: Path,
    project_root: Path,
) -> VerbatimValidationResult:
    """Construye en staging, valida y solo entonces reemplaza el destino."""

    corpus = extract_verbatim_corpus(
        pdf_path,
        document_id=document_id,
        source_file=source_file,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
    ) as staging_directory:
        candidate_path = Path(staging_directory) / output_path.name
        write_verbatim_corpus(corpus, candidate_path)
        result = validate_verbatim_artifact(
            candidate_path,
            project_root=project_root,
        )
        candidate_path.replace(output_path)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un JSON verbatim por páginas y lo revalida contra el PDF.",
    )
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = export_verbatim_document(
        pdf_path=args.pdf,
        document_id=args.document_id,
        source_file=args.source_file,
        output_path=args.output,
        project_root=args.project_root,
    )
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "artifact_sha256": result.artifact_sha256,
                "document_id": result.document_id,
                "page_count": result.page_count,
                "pages_sha256": result.pages_sha256,
                "source_sha256": result.source_sha256,
                "status": result.status,
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
