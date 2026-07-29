"""Invariantes de revisión y trazabilidad literal de la fuente."""

from copy import deepcopy

import pytest
from jurisprudence_case_v3_factory import valid_case
from pydantic import ValidationError


def test_aprobacion_juridica_humana_exige_identidad_humana_y_fecha() -> None:
    from jurisprudence_case_source import ReviewStatus

    with pytest.raises(ValidationError, match="human:"):
        ReviewStatus.model_validate(
            {
                "technical": "VALIDATED",
                "legal": "HUMAN_APPROVED",
                "reviewed_by": "agent:codex",
                "reviewed_at": None,
                "notes": None,
            }
        )


def test_revision_del_agente_no_puede_presentarse_como_humana() -> None:
    from jurisprudence_case_source import ReviewStatus

    with pytest.raises(ValidationError, match="AGENT_REVIEWED"):
        ReviewStatus.model_validate(
            {
                "technical": "VALIDATED",
                "legal": "AGENT_REVIEWED",
                "reviewed_by": "human:abogado",
                "reviewed_at": "2026-07-29",
                "notes": None,
            }
        )


def test_fragmento_rechaza_offsets_vacios_o_invertidos() -> None:
    from jurisprudence_case_source import SourceFragment

    with pytest.raises(ValidationError, match="end_offset"):
        SourceFragment.model_validate(
            {
                "page_index": 8,
                "printed_page": "8",
                "start_offset": 124,
                "end_offset": 100,
                "verbatim_text": "texto exacto",
            }
        )


def test_elipsis_exige_al_menos_dos_fragmentos_literales() -> None:
    from jurisprudence_case_source import SourceAnchor

    anchor = valid_case()["source_anchors"][0]
    anchor["fidelity"] = "EXACT_WITH_ELLIPSIS"

    with pytest.raises(ValidationError, match="dos fragmentos"):
        SourceAnchor.model_validate(anchor)


def test_anclaje_exacto_contiene_un_solo_fragmento() -> None:
    from jurisprudence_case_source import SourceAnchor

    anchor = deepcopy(valid_case()["source_anchors"][0])
    second_fragment = deepcopy(anchor["fragments"][0])
    second_fragment["start_offset"] = 200
    second_fragment["end_offset"] = 212
    anchor["fragments"].append(second_fragment)

    with pytest.raises(ValidationError, match="un fragmento"):
        SourceAnchor.model_validate(anchor)


def test_fragmentos_con_elipsis_permanecen_ordenados() -> None:
    from jurisprudence_case_source import SourceAnchor

    anchor = deepcopy(valid_case()["source_anchors"][0])
    anchor["fidelity"] = "EXACT_WITH_ELLIPSIS"
    earlier_fragment = deepcopy(anchor["fragments"][0])
    earlier_fragment["page_index"] = 7
    anchor["fragments"].append(earlier_fragment)

    with pytest.raises(ValidationError, match="ordenados"):
        SourceAnchor.model_validate(anchor)
