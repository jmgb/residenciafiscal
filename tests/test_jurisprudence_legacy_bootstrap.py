"""Bootstrap conservador de los registros legados al contrato v3."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from verbatim_artifact import write_verbatim_corpus
from verbatim_hashing import sha256_canonical_pages, sha256_utf8
from verbatim_models import VerbatimCorpus


def _verbatim() -> VerbatimCorpus:
    raw_pages = (
        "JURISPRUDENCIA\nRoj: SAN 1/2026 - ECLI:ES:AN:2026:1\n",
        (
            "La Sala considera acreditada la residencia fiscal en España por el centro "
            "de intereses económicos.\nFALLAMOS\nDESESTIMAR el recurso.\n"
        ),
    )
    pages = [
        {
            "page_index": index,
            "printed_page": str(index),
            "raw_page_text": text,
            "text_sha256": sha256_utf8(text),
            "extraction_status": "TEXT_EXTRACTED",
        }
        for index, text in enumerate(raw_pages, 1)
    ]
    return VerbatimCorpus.model_validate(
        {
            "schema_version": "residenciafiscal-verbatim/1",
            "document_id": "san-1-2026",
            "source_file": "sentencias/SAN_1_2026.pdf",
            "source_sha256": "a" * 64,
            "extractor": {"name": "pypdf", "version": "6.14.2"},
            "page_count": 2,
            "pages_sha256": sha256_canonical_pages(pages),
            "status": "COMPLETE",
            "pages": pages,
        }
    )


def _legacy_record() -> dict[str, object]:
    return {
        "archivo": "SAN_1_2026.pdf",
        "identificadores": {"ROJ": "SAN 1/2026", "ECLI": "ECLI:ES:AN:2026:1"},
        "organo": "Audiencia Nacional. Sala de lo Contencioso-Administrativo",
        "fecha_resolucion": "2026-01-15",
        "es_caso_residencia_irpf": "SI",
        "ejercicios_afectados": "2020 y 2021",
        "pais_alegado_residencia_pf": "Francia",
        "Criterios_residencia_detectados": ["CRIT_CENTRO_INTERESES_ECONOMICOS"],
        "resumen_criterios": "El centro de intereses económicos se situó en España.",
        "razonamiento_residencia": "La Sala consideró acreditada la residencia en España.",
        "Pruebas_AEAT": [
            {
                "categoria": "ACTIVIDAD_ECONOMICA_Y_GESTION",
                "subcategoria": "centro de intereses",
                "detalle": "Actividad económica desarrollada en España.",
                "objetivo_probatorio": "Acreditar la residencia fiscal.",
                "aceptada": "SI",
                "motivo_valoracion": "La Sala la consideró acreditada.",
                "cita": {
                    "pagina": "2",
                    "texto": (
                        "La Sala considera acreditada la residencia fiscal en España "
                        "por el centro de intereses económicos."
                    ),
                },
            }
        ],
        "Pruebas_contribuyente": [],
        "doctrina_citada": ["Artículo 9 LIRPF"],
        "carga_prueba": {"quien_tenia_carga": "AEAT", "cumplida": "SI"},
        "resultado_final": "GANA_AEAT",
        "frases_clave": [],
        "confianza_extraccion": "ALTA",
    }


def test_localiza_un_fragmento_literal_sin_reconstruir_la_cita() -> None:
    from jurisprudence_legacy_anchors import locate_exact_fragments

    fragments = locate_exact_fragments(
        "residencia fiscal en España ... centro de intereses económicos",
        declared_page="2",
        verbatim=_verbatim(),
    )

    assert tuple(item.page_index for item in fragments) == (2, 2)
    assert tuple(item.verbatim_text for item in fragments) == (
        "residencia fiscal en España",
        "centro de intereses económicos",
    )
    assert all(
        item.verbatim_text
        == _verbatim().pages[item.page_index - 1].raw_page_text[item.start_offset : item.end_offset]
        for item in fragments
    )


def test_ordena_los_fragmentos_por_su_posicion_real_en_el_pdf() -> None:
    from jurisprudence_legacy_anchors import locate_exact_fragments

    fragments = locate_exact_fragments(
        "DESESTIMAR el recurso ... Roj: SAN 1/2026",
        declared_page="2",
        verbatim=_verbatim(),
    )

    assert tuple(item.page_index for item in fragments) == (1, 2)


def test_construye_una_propuesta_minima_valida_y_evaluable(tmp_path: Path) -> None:
    from jurisprudence_case_compilation import compile_case_proposal
    from jurisprudence_case_question_evaluation import (
        CaseQuestionEvaluation,
        validate_question_evaluation,
    )
    from jurisprudence_legacy_draft import build_legacy_case_draft

    verbatim = _verbatim()
    verbatim_path = tmp_path / "knowledge/verbatim/san-1-2026.pages.json"
    legacy_path = tmp_path / "output/analisis.jsonl"
    write_verbatim_corpus(verbatim, verbatim_path)
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(json.dumps(_legacy_record()) + "\n", encoding="utf-8")

    draft = build_legacy_case_draft(
        _legacy_record(),
        verbatim=verbatim,
        verbatim_resource="knowledge/verbatim/san-1-2026.pages.json",
        legacy_resource="output/analisis.jsonl",
        generated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    case = compile_case_proposal(
        draft.proposal,
        verbatim=verbatim,
        verbatim_path=verbatim_path,
        project_root=tmp_path,
    )
    evaluation = CaseQuestionEvaluation.model_validate(draft.evaluation)

    assert case.judgment.judgment_id == "san-1-2026"
    assert case.judgment.review.legal == "AGENT_REVIEWED"
    assert case.holdings[0].residence_determination is not None
    assert case.holdings[0].residence_determination.spanish_residence == "NOT_DECIDED"
    assert case.source_anchors[0].fragments[0].verbatim_text.startswith("La Sala")
    assert validate_question_evaluation(evaluation, case).question_count == 1
    assert "centro de intereses" in evaluation.questions[0].question


def test_conserva_anclajes_literales_de_valoracion_resultado_y_carga() -> None:
    from jurisprudence_legacy_draft import build_legacy_case_draft

    record = _legacy_record() | {
        "carga_prueba": {
            "quien_tenia_carga": "AEAT",
            "cumplida": "NO",
            "motivo": "La Administración no acreditó el presupuesto residencial.",
            "cita": {
                "pagina": "2",
                "texto": "La Sala considera acreditada la residencia fiscal en España",
            },
        },
        "Pruebas_rechazadas_clave": [
            {
                "parte": "AEAT",
                "categoria": "ACTIVIDAD_ECONOMICA_Y_GESTION",
                "subcategoria": "centro de intereses",
                "cita": {
                    "pagina": "2",
                    "texto": "por el centro de intereses económicos",
                },
            }
        ],
        "frases_clave": [
            {
                "tema": "resultado",
                "pagina": "2",
                "texto": "FALLAMOS\nDESESTIMAR el recurso.",
            }
        ],
    }

    draft = build_legacy_case_draft(
        record,
        verbatim=_verbatim(),
        verbatim_resource="knowledge/verbatim/san-1-2026.pages.json",
        legacy_resource="output/analisis.jsonl",
        generated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    purposes_by_id = {
        item["anchor_id"]: item["purpose"] for item in draft.proposal["source_anchors"]
    }
    assert {"HOLDING", "REASONING", "BURDEN_OF_PROOF"} <= set(purposes_by_id.values())
    assert all(
        purposes_by_id[anchor_id] == "HOLDING"
        for anchor_id in draft.proposal["holdings"][0]["anchor_ids"]
    )
    assert draft.proposal["burden_of_proof_steps"] == [
        {
            "step_id": "burden-legacy-001",
            "sequence": 1,
            "issue_ids": ["residencia-fiscal"],
            "fact_to_prove": "La Administración no acreditó el presupuesto residencial.",
            "initial_bearer": "AEAT",
            "triggering_evidence_ids": [],
            "shifts_to": None,
            "response_required": None,
            "conclusion": "La carga probatoria no se consideró cumplida.",
            "anchor_ids": [
                next(
                    anchor_id
                    for anchor_id, purpose in purposes_by_id.items()
                    if purpose == "BURDEN_OF_PROOF"
                )
            ],
            "review": draft.proposal["review"],
        }
    ]


def test_conserva_fuera_de_alcance_sin_convertirlo_en_residencia() -> None:
    from jurisprudence_legacy_draft import build_legacy_case_draft

    record = _legacy_record() | {
        "es_caso_residencia_irpf": "NO",
        "motivo_fuera_de_alcance": "La resolución no decide residencia fiscal.",
        "resultado_final": "FUERA_DE_ALCANCE",
        "Pruebas_AEAT": [],
    }
    draft = build_legacy_case_draft(
        record,
        verbatim=_verbatim(),
        verbatim_resource="knowledge/verbatim/san-1-2026.pages.json",
        legacy_resource="output/analisis.jsonl",
        generated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    assert draft.proposal["judgment"]["is_tax_residence_case"] is False
    assert draft.proposal["legal_issues"][0]["issue_type"] == "OTHER"
    assert draft.proposal["holdings"][0]["residence_determination"] is None
