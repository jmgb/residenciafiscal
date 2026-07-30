"""Valida una propuesta aislada de mejora del corpus jurisprudencial."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CandidateValidationResult:
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_path(root: Path, raw_path: object, errors: list[str], scope: str) -> Path | None:
    if not isinstance(raw_path, str):
        errors.append(f"{scope}: falta una ruta relativa")
        return None
    path = (root / raw_path).resolve()
    if not path.is_relative_to(root.resolve()):
        errors.append(f"{scope}: la ruta sale del repositorio")
        return None
    if not path.is_file():
        errors.append(f"{scope}: no existe {raw_path}")
        return None
    return path


def _validate_source(
    source: Mapping[str, Any],
    *,
    index: int,
    project_root: Path,
    errors: list[str],
) -> None:
    scope = f"sources[{index}]"
    pdf = _safe_path(project_root, source.get("source_file"), errors, f"{scope}/source_file")
    verbatim_path = _safe_path(
        project_root, source.get("verbatim_path"), errors, f"{scope}/verbatim_path"
    )
    if pdf and source.get("source_sha256") != _sha256(pdf):
        errors.append(f"{scope}/source_sha256: no coincide con el PDF")
    if verbatim_path is None:
        return
    if source.get("verbatim_sha256") != _sha256(verbatim_path):
        errors.append(f"{scope}/verbatim_sha256: no coincide con el verbatim")

    verbatim = json.loads(verbatim_path.read_bytes())
    if verbatim.get("document_id") != source.get("judgment_id"):
        errors.append(f"{scope}/judgment_id: no coincide con el verbatim")
    if verbatim.get("source_file") != source.get("source_file"):
        errors.append(f"{scope}/source_file: no coincide con el verbatim")
    if verbatim.get("source_sha256") != source.get("source_sha256"):
        errors.append(f"{scope}/source_sha256: no coincide con el verbatim")

    page_index = source.get("page_index")
    page = next(
        (item for item in verbatim.get("pages", []) if item.get("page_index") == page_index),
        None,
    )
    if page is None:
        errors.append(f"{scope}/page_index: página inexistente")
        return
    quote = source.get("quote")
    if not isinstance(quote, str) or quote not in page.get("raw_page_text", ""):
        errors.append(f"{scope}/quote: no es subcadena literal de la página")
    if source.get("fidelity") != "EXACT":
        errors.append(f"{scope}/fidelity: debe ser EXACT")


def validate_candidate(
    candidate: Mapping[str, Any],
    *,
    project_root: Path,
) -> CandidateValidationResult:
    errors: list[str] = []
    if candidate.get("schema_version") != "residenciafiscal-chat-data-gap-candidate/1":
        errors.append("schema_version: versión no admitida")
    if candidate.get("status") != "PROPOSED_NOT_APPLIED":
        errors.append("status: debe ser PROPOSED_NOT_APPLIED")
    if candidate.get("requires_human_legal_review") is not True:
        errors.append("requires_human_legal_review: debe ser true")
    if candidate.get("canonical_outputs_modified") is not False:
        errors.append("canonical_outputs_modified: debe ser false")
    sources = candidate.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources: debe contener al menos una fuente")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"sources[{index}]: debe ser un objeto")
                continue
            _validate_source(source, index=index, project_root=project_root, errors=errors)
    return CandidateValidationResult(errors=tuple(errors))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    candidate = json.loads(args.candidate.read_bytes())
    result = validate_candidate(candidate, project_root=args.project_root)
    if result.valid:
        print("Propuesta aislada válida; el corpus canónico no se ha modificado")
        return 0
    for error in result.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
