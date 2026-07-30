"""Fase D: conducta, recuperación estructurada y evaluación ciega."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval/corpus.json"
PILOT_PATH = PROJECT_ROOT / "docs/experiments/CHAT_QUESTION_PILOT_5.md"
PARAPHRASES_PATH = PROJECT_ROOT / "docs/experiments/CHAT_QUESTION_PARAPHRASES_5.json"


def _corpus():
    from jurisprudence_retrieval_corpus import load_retrieval_corpus

    return load_retrieval_corpus(CORPUS_PATH.read_bytes())


def test_banco_de_parafrasis_es_independiente_y_hereda_la_verdad_de_referencia() -> None:
    from jurisprudence_phase_d_evaluation import (
        load_paraphrase_bank,
        materialize_paraphrase_bank,
    )
    from jurisprudence_sample_evaluation import parse_question_pilot

    source = parse_question_pilot(PILOT_PATH)
    definitions = load_paraphrase_bank(PARAPHRASES_PATH)
    bank = materialize_paraphrase_bank(definitions, source)

    assert len(bank.questions) == 20
    assert len({item.question for item in bank.questions}) == 20
    by_id = {item.question_id: item for item in bank.questions}
    assert by_id["PAR-DAY-05"].behavior == "abstenerse"
    assert by_id["PAR-GEN-01"].expected_judgment_ids == (
        "san-1210-2023",
        "san-1071-2025",
    )


def test_analisis_de_consulta_extrae_facetas_y_detecta_cobertura_ausente() -> None:
    from jurisprudence_query_analysis import analyze_query

    family = analyze_query(
        "Trabajo fuera, pero mi pareja y mis hijos viven en España.",
        _corpus(),
    )
    absences = analyze_query(
        "¿Cuándo computan como ausencias esporádicas mis viajes al extranjero?",
        _corpus(),
    )

    assert "CRIT_PRESUNCION_FAMILIA" in family.criterion_ids
    assert "FAMILIA_Y_ENTORNO_PERSONAL" in family.evidence_categories
    assert family.is_personal_case is True
    assert absences.uncovered_facets == ("CRIT_AUSENCIAS_ESPORADICAS",)


def test_router_no_devuelve_fuentes_si_debe_preguntar_o_abstenerse() -> None:
    from jurisprudence_phase_d_retrieval import retrieve_for_chat

    ask = retrieve_for_chat(
        _corpus(),
        "¿Cuál de estas sentencias se parece más a mi situación personal?",
    )
    abstain = retrieve_for_chat(
        _corpus(),
        "¿Cuándo computan las ausencias esporádicas?",
    )

    assert ask.behavior == "preguntar"
    assert ask.hits == ()
    assert ask.missing_facts
    assert abstain.behavior == "abstenerse"
    assert abstain.hits == ()
    assert abstain.uncovered_facets == ("CRIT_AUSENCIAS_ESPORADICAS",)


def test_router_se_abstiene_fuera_del_dominio_jurisprudencial() -> None:
    from jurisprudence_phase_d_retrieval import retrieve_for_chat

    result = retrieve_for_chat(
        _corpus(),
        "¿Qué plazo tengo para presentar una demanda laboral por despido?",
    )

    assert result.behavior == "abstenerse"
    assert result.hits == ()
    assert result.uncovered_facets == ("OUT_OF_SCOPE",)


def test_recuperacion_responde_con_fuentes_diversas_y_roles_explicitos() -> None:
    from jurisprudence_phase_d_retrieval import retrieve_for_chat

    result = retrieve_for_chat(
        _corpus(),
        "¿Con qué indicios acredita Hacienda la residencia fiscal en España?",
        limit=4,
    )

    assert result.behavior == "responder"
    assert 2 <= len(result.hits) <= 4
    assert len({item.judgment_id for item in result.hits}) == len(result.hits)
    assert {"support", "contrast"} <= {item.role for item in result.hits}
    assert all(item.source_anchors for item in result.hits)
    assert all(item.score.lexical >= 0 for item in result.hits)
    assert all(item.score.total >= item.score.lexical for item in result.hits)


def test_direccion_residencial_usa_la_faceta_tipadada_y_no_el_texto_libre() -> None:
    from jurisprudence_phase_d_retrieval import retrieval_case_side

    unit = next(item for item in _corpus().units if item.judgment_id == "san-1226-2021")
    contradictory = unit.model_copy(
        update={
            "holding": unit.holding.model_copy(
                update={"conclusion": "El recurrente tenía residencia en España."}
            )
        }
    )
    untyped = contradictory.model_copy(
        update={"facets": contradictory.facets.model_copy(update={"residence_determination": None})}
    )

    assert retrieval_case_side(contradictory) == "resident_abroad"
    assert retrieval_case_side(untyped) == "mixed"


def test_evaluacion_separa_original_y_parafrasis_y_aplica_gates() -> None:
    from jurisprudence_phase_d_evaluation import (
        evaluate_phase_d,
        load_paraphrase_bank,
        materialize_paraphrase_bank,
    )
    from jurisprudence_sample_evaluation import parse_question_pilot

    original = parse_question_pilot(PILOT_PATH)
    paraphrases = materialize_paraphrase_bank(
        load_paraphrase_bank(PARAPHRASES_PATH),
        original,
    )
    report = evaluate_phase_d(
        corpus=_corpus(),
        original_bank=original,
        paraphrase_bank=paraphrases,
    )

    assert report.schema_version == "residenciafiscal-phase-d-evaluation/1"
    assert report.original.question_count == 40
    assert report.paraphrases.question_count == 20
    assert report.original.behavior_accuracy >= 0.90
    assert report.paraphrases.behavior_accuracy >= 0.80
    assert report.original.zero_source_safety == 1
    assert report.paraphrases.zero_source_safety == 1
    assert report.candidate.expected_recall_at_3 >= report.baseline.expected_recall_at_3
    assert report.candidate.contrast_recall_at_3 >= 0.80
    assert report.embedding_decision == "NOT_REQUIRED_FOR_PILOT"
    assert report.gate_status == "PASSED"


def test_exporta_informe_de_fase_d_reproducible_y_con_huellas(
    tmp_path: Path,
) -> None:
    from export_jurisprudence_phase_d import export_phase_d_evaluation

    output = tmp_path / "phase-d-retrieval-evaluation.json"
    kwargs = {
        "corpus_path": CORPUS_PATH,
        "pilot_path": PILOT_PATH,
        "paraphrases_path": PARAPHRASES_PATH,
        "output_path": output,
    }
    first = export_phase_d_evaluation(**kwargs)
    first_payload = output.read_bytes()
    second = export_phase_d_evaluation(**kwargs)

    assert first_payload == output.read_bytes()
    assert first.report == second.report
    assert first.report.inputs.corpus_sha256
    assert first.report.inputs.original_bank_sha256
    assert first.report.inputs.paraphrase_bank_sha256
    assert first.report.gate_status == "PASSED"


def test_export_rechaza_parafrasis_de_otra_muestra(tmp_path: Path) -> None:
    from export_jurisprudence_phase_d import export_phase_d_evaluation

    payload = json.loads(PARAPHRASES_PATH.read_text(encoding="utf-8"))
    payload["sample_id"] = "otra-muestra"
    paraphrases = tmp_path / "paraphrases.json"
    paraphrases.write_text(json.dumps(payload), encoding="utf-8")

    try:
        export_phase_d_evaluation(
            corpus_path=CORPUS_PATH,
            pilot_path=PILOT_PATH,
            paraphrases_path=paraphrases,
            output_path=tmp_path / "report.json",
        )
    except ValueError as error:
        assert "sample_id" in str(error)
    else:
        raise AssertionError("debió rechazar un banco de otra muestra")
