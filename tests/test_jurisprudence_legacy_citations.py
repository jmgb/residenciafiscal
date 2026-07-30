"""Cierre explícito de las 17 citas heredadas no publicables."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS_PATH = (
    PROJECT_ROOT / "knowledge/jurisprudencia-v3/evaluations/legacy-citation-dispositions.json"
)


def test_clasifica_las_diecisiete_citas_sin_pendientes() -> None:
    from jurisprudence_legacy_citations import (
        load_legacy_citation_dispositions,
        validate_legacy_citation_dispositions,
    )

    dispositions = load_legacy_citation_dispositions(DISPOSITIONS_PATH)
    result = validate_legacy_citation_dispositions(
        dispositions,
        legacy_reports_root=(PROJECT_ROOT / "knowledge/jurisprudencia-muestra-5/reports"),
        cases_root=PROJECT_ROOT / "knowledge/jurisprudencia-v3/cases",
    )

    assert result.total == 17
    assert result.replaced_by_exact_anchor == 15
    assert result.retired_as_paraphrase == 2
    assert result.unclassified == 0


def test_reemplazo_exige_un_anclaje_de_fidelidad_exact(
    tmp_path: Path,
) -> None:
    from jurisprudence_legacy_citations import (
        load_legacy_citation_dispositions,
        validate_legacy_citation_dispositions,
    )

    cases_root = tmp_path / "cases"
    shutil.copytree(
        PROJECT_ROOT / "knowledge/jurisprudencia-v3/cases",
        cases_root,
    )
    case_path = cases_root / "san-1071-2025.case.json"
    case = json.loads(case_path.read_text(encoding="utf-8"))
    anchor = next(
        item for item in case["source_anchors"] if item["anchor_id"] == "anchor-actividad-tarjetas"
    )
    fragment = anchor["fragments"][0]
    split = len(fragment["verbatim_text"]) // 2
    anchor["fidelity"] = "EXACT_WITH_ELLIPSIS"
    anchor["fragments"] = [
        {
            **fragment,
            "end_offset": fragment["start_offset"] + split,
            "verbatim_text": fragment["verbatim_text"][:split],
        },
        {
            **fragment,
            "start_offset": fragment["start_offset"] + split,
            "verbatim_text": fragment["verbatim_text"][split:],
        },
    ]
    case_path.write_text(
        json.dumps(case, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="fidelidad EXACT"):
        validate_legacy_citation_dispositions(
            load_legacy_citation_dispositions(DISPOSITIONS_PATH),
            legacy_reports_root=(PROJECT_ROOT / "knowledge/jurisprudencia-muestra-5/reports"),
            cases_root=cases_root,
        )
