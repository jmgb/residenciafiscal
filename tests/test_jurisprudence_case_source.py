"""Invariantes de revisión y trazabilidad literal de la fuente."""

from copy import deepcopy

import pytest
from jurisprudence_case_v3_factory import valid_case
from pydantic import ValidationError


def test_procedencia_del_analisis_exige_entradas_tipadas() -> None:
    from jurisprudence_case_source import AnalysisProvenance

    with pytest.raises(ValidationError, match="input_artifacts"):
        AnalysisProvenance.model_validate(
            {
                "producer": "residenciafiscal-agent-pipeline",
                "model_id": "codex-agent",
                "prompt_sha256": None,
                "run_id": "case-v3-pilot",
                "generated_at": "2026-07-29T12:00:00Z",
                "notes": None,
            }
        )


def test_procedencia_identifica_verbatim_analisis_y_sidecar() -> None:
    from jurisprudence_case_source import AnalysisProvenance

    provenance = AnalysisProvenance.model_validate(
        {
            "producer": "residenciafiscal-agent-pipeline",
            "model_id": "codex-agent",
            "prompt_sha256": None,
            "run_id": "case-v3-pilot",
            "generated_at": "2026-07-29T12:00:00Z",
            "input_artifacts": [
                {
                    "kind": "VERBATIM",
                    "source_path": "knowledge/verbatim/case.pages.json",
                    "sha256": "a" * 64,
                },
                {
                    "kind": "LEGACY_ANALYSIS",
                    "source_path": "knowledge/sources/case.analysis.json",
                    "sha256": "b" * 64,
                },
                {
                    "kind": "ANNOTATIONS",
                    "source_path": "knowledge/annotations/case.yaml",
                    "sha256": "c" * 64,
                },
            ],
            "notes": None,
        }
    )

    assert [item.kind for item in provenance.input_artifacts] == [
        "VERBATIM",
        "LEGACY_ANALYSIS",
        "ANNOTATIONS",
    ]


def test_procedencia_exige_exactamente_un_verbatim() -> None:
    from jurisprudence_case_source import AnalysisProvenance

    with pytest.raises(ValidationError, match="exactamente una entrada VERBATIM"):
        AnalysisProvenance.model_validate(
            {
                "producer": "residenciafiscal-agent-pipeline",
                "generated_at": "2026-07-29T12:00:00Z",
                "input_artifacts": [
                    {
                        "kind": "OTHER",
                        "source_path": "knowledge/source.json",
                        "sha256": "a" * 64,
                    }
                ],
            }
        )


@pytest.mark.parametrize("source_path", ["/tmp/source.json", "../source.json", r"a\b.json"])
def test_procedencia_exige_rutas_relativas_portables(source_path: str) -> None:
    from jurisprudence_case_source import AnalysisInputArtifact

    with pytest.raises(ValidationError, match="relativa y portable"):
        AnalysisInputArtifact.model_validate(
            {
                "kind": "OTHER",
                "source_path": source_path,
                "sha256": "a" * 64,
            }
        )


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
