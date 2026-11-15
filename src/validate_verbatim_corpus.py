"""Reextrae el corpus del manifiesto sin entradas históricas ni escrituras."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from jurisprudence_rollout import load_rollout_manifest
from verbatim_artifact import load_verbatim_corpus
from verbatim_validation import VerbatimValidationResult, validate_verbatim_artifact


def validate_verbatim_corpus(
    *, project_root: Path, manifest_path: Path, verbatim_root: Path
) -> tuple[VerbatimValidationResult, ...]:
    manifest = load_rollout_manifest(manifest_path)
    expected = {f"{document.judgment_id}.pages.json" for document in manifest.documents}
    actual = {path.name for path in verbatim_root.glob("*.pages.json")}
    if actual != expected:
        raise ValueError(
            f"cobertura verbatim incorrecta: faltan {sorted(expected - actual)}, "
            f"sobran {sorted(actual - expected)}"
        )

    results = []
    for document in manifest.documents:
        path = verbatim_root / f"{document.judgment_id}.pages.json"
        artifact = load_verbatim_corpus(path.read_bytes())
        if (
            artifact.document_id != document.judgment_id
            or artifact.source_file != document.source_file
            or artifact.source_sha256 != document.source_sha256
        ):
            raise ValueError(f"{document.judgment_id}: el verbatim no corresponde al manifiesto")
        results.append(validate_verbatim_artifact(path, project_root=project_root))
    return tuple(results)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--manifest", type=Path, default=Path("sentencias/jurisprudence_v3_rollout_106.json")
    )
    parser.add_argument(
        "--verbatim-root", type=Path, default=Path("knowledge/jurisprudencia-v3/verbatim")
    )
    args = parser.parse_args(argv)
    results = validate_verbatim_corpus(
        project_root=args.project_root,
        manifest_path=args.project_root / args.manifest,
        verbatim_root=args.project_root / args.verbatim_root,
    )
    print(
        json.dumps(
            {
                "documents": len(results),
                "pages": sum(result.page_count for result in results),
                "validation": "passed",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
