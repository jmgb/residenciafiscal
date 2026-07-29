"""Compilación determinista del aporte del agente al contrato v3."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jurisprudence_case_artifact import write_jurisprudence_case
from jurisprudence_case_models import JurisprudenceCase
from okf_provenance import sha256_file
from verbatim_artifact import load_verbatim_corpus
from verbatim_models import VerbatimCorpus


def _resolve_input(project_root: Path, source_path: str) -> Path:
    resolved_root = project_root.resolve()
    resolved_path = (resolved_root / source_path).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError("input_artifacts contiene una ruta fuera de project_root")
    if not resolved_path.is_file():
        raise ValueError(f"input_artifacts no existe: {source_path}")
    return resolved_path


def _resolve_fragment(fragment: dict[str, Any], verbatim: VerbatimCorpus) -> None:
    page_index = fragment.get("page_index")
    if not isinstance(page_index, int) or not 1 <= page_index <= verbatim.page_count:
        raise ValueError(f"page_index inválido: {page_index}")
    text = fragment.get("verbatim_text")
    if not isinstance(text, str) or not text:
        raise ValueError("verbatim_text debe ser texto no vacío")
    page = verbatim.pages[page_index - 1]
    occurrence_count = page.raw_page_text.count(text)
    if occurrence_count != 1:
        raise ValueError(
            f"la cita de la página {page_index} debe aparecer exactamente una vez; "
            f"aparece {occurrence_count}"
        )
    start_offset = page.raw_page_text.index(text)
    fragment["printed_page"] = page.printed_page
    fragment["start_offset"] = start_offset
    fragment["end_offset"] = start_offset + len(text)


def compile_case_proposal(
    proposal: dict[str, Any],
    *,
    verbatim: VerbatimCorpus,
    project_root: Path,
) -> JurisprudenceCase:
    """Inyecta metadatos mecánicos sin modificar el contenido jurídico."""

    raw = deepcopy(proposal)
    judgment = raw["judgment"]
    if judgment.get("judgment_id") != verbatim.document_id:
        raise ValueError("judgment_id de la propuesta no coincide con el verbatim")
    declared_source = judgment.get("source_file")
    if declared_source is not None and declared_source != verbatim.source_file:
        raise ValueError("source_file de la propuesta no coincide con el verbatim")
    judgment["source_file"] = verbatim.source_file
    judgment["source_sha256"] = verbatim.source_sha256
    judgment["page_count"] = verbatim.page_count
    judgment["extractor"] = verbatim.extractor.model_dump(mode="json")

    provenance = judgment["analysis_provenance"]
    for artifact in provenance["input_artifacts"]:
        input_path = _resolve_input(project_root, artifact["source_path"])
        artifact["sha256"] = sha256_file(input_path)

    for anchor in raw["source_anchors"]:
        anchor["source_sha256"] = verbatim.source_sha256
        for fragment in anchor["fragments"]:
            _resolve_fragment(fragment, verbatim)
    return JurisprudenceCase.model_validate(raw)


def build_case_artifact(
    proposal_path: Path,
    *,
    verbatim_path: Path,
    project_root: Path,
    destination: Path,
) -> Path:
    """Compila archivos de entrada y persiste el caso canónico."""

    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    verbatim = load_verbatim_corpus(verbatim_path.read_bytes())
    case = compile_case_proposal(
        proposal,
        verbatim=verbatim,
        project_root=project_root,
    )
    return write_jurisprudence_case(case, destination)
