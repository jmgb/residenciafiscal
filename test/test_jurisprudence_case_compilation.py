"""Compilación determinista de propuestas híbridas a casos v3."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jurisprudence_case_v3_factory import valid_case
from test_jurisprudence_case_verbatim_validation import _verbatim


def _proposal(source_path: str) -> dict[str, Any]:
    raw = deepcopy(valid_case())
    judgment = raw["judgment"]
    del judgment["source_sha256"]
    del judgment["page_count"]
    del judgment["extractor"]
    judgment["analysis_provenance"]["input_artifacts"] = [
        {"kind": "VERBATIM", "source_path": source_path}
    ]
    fragment = raw["source_anchors"][0]["fragments"][0]
    del raw["source_anchors"][0]["source_sha256"]
    del fragment["printed_page"]
    del fragment["start_offset"]
    del fragment["end_offset"]
    return raw


def test_compilador_resuelve_fuentes_hashes_y_offsets(tmp_path: Path) -> None:
    from jurisprudence_case_compilation import compile_case_proposal
    from verbatim_artifact import write_verbatim_corpus

    source_path = "knowledge/verbatim/case.pages.json"
    artifact_path = tmp_path / source_path
    write_verbatim_corpus(_verbatim(), artifact_path)

    case = compile_case_proposal(
        _proposal(source_path),
        verbatim=_verbatim(),
        project_root=tmp_path,
    )

    fragment = case.source_anchors[0].fragments[0]
    assert fragment.start_offset == 100
    assert fragment.end_offset == 128
    assert fragment.printed_page == "8"
    assert case.source_anchors[0].source_sha256 == "a" * 64
    assert case.judgment.analysis_provenance.input_artifacts[0].sha256 != "c" * 64


@pytest.mark.parametrize("page_text", ["sin coincidencia", "cita cita"])
def test_compilador_exige_una_unica_coincidencia_literal(
    tmp_path: Path,
    page_text: str,
) -> None:
    from jurisprudence_case_compilation import compile_case_proposal
    from verbatim_artifact import write_verbatim_corpus
    from verbatim_hashing import sha256_canonical_pages, sha256_utf8
    from verbatim_models import VerbatimCorpus

    raw_verbatim = _verbatim().model_dump(mode="json")
    raw_verbatim["pages"][7]["raw_page_text"] = page_text
    raw_verbatim["pages"][7]["text_sha256"] = sha256_utf8(page_text)
    raw_verbatim["pages_sha256"] = sha256_canonical_pages(raw_verbatim["pages"])
    verbatim = VerbatimCorpus.model_validate(raw_verbatim)
    source_path = "knowledge/verbatim/case.pages.json"
    write_verbatim_corpus(verbatim, tmp_path / source_path)
    proposal = _proposal(source_path)
    proposal["source_anchors"][0]["fragments"][0]["verbatim_text"] = "cita"

    with pytest.raises(ValueError, match="exactamente una"):
        compile_case_proposal(proposal, verbatim=verbatim, project_root=tmp_path)
