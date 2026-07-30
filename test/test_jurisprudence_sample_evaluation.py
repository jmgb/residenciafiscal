"""Banco de 40 preguntas y evaluación ejecutable del índice agregado."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = PROJECT_ROOT / "docs/experiments/CHAT_QUESTION_PILOT_5.md"
RETRIEVAL_ROOT = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval"
MANIFEST_PATH = PROJECT_ROOT / "sentencias/jurisprudence_v3_sample_5.json"
SAMPLE_BUILD_PATH = PROJECT_ROOT / "knowledge/jurisprudencia-v3/sample-build.json"


def test_extrae_las_cuarenta_preguntas_y_sus_contrastes() -> None:
    from jurisprudence_sample_evaluation import parse_question_pilot

    bank = parse_question_pilot(PILOT_PATH)

    assert bank.schema_version == "residenciafiscal-retrieval-evaluation-bank/1"
    assert len(bank.questions) == 40
    by_id = {item.question_id: item for item in bank.questions}
    assert by_id["GEN-01"].expected_judgment_ids == (
        "san-1210-2023",
        "san-1071-2025",
    )
    assert by_id["GEN-01"].contrast_judgment_ids == (
        "san-1226-2021",
        "san-1386-2017",
    )
    assert by_id["CMP-02"].expected_judgment_ids == ()
    assert len(by_id["PRE-01"].expected_judgment_ids) == 5


def test_ejecuta_el_banco_completo_con_trazabilidad() -> None:
    from jurisprudence_retrieval_corpus import build_retrieval_corpus
    from jurisprudence_sample_evaluation import (
        evaluate_question_bank,
        parse_question_pilot,
    )

    corpus = build_retrieval_corpus(
        tuple(sorted(RETRIEVAL_ROOT.glob("san-*.issues.json"))),
        sample_id="jurisprudencia-v3-piloto-5",
        project_root=PROJECT_ROOT,
    )
    report = evaluate_question_bank(parse_question_pilot(PILOT_PATH), corpus)

    assert report.schema_version == "residenciafiscal-retrieval-evaluation-report/2"
    assert report.question_count == 40
    assert len(report.results) == 40
    assert all(result.retrieved_unit_ids_at_12 for result in report.results)
    assert report.expected_recall_at_12 == 1
    assert report.contrast_recall_at_12 == 1
    assert report.evaluation_scope == "RETRIEVAL_ONLY"
    assert report.chat_behavior_gate == "NOT_EVALUATED"
    assert report.expected_behavior_counts == {
        "abstenerse": 1,
        "parcial": 12,
        "preguntar": 7,
        "responder": 20,
    }
    by_id = {item.question_id: item for item in report.results}
    assert by_id["CMP-02"].expected_behavior == "preguntar"
    assert by_id["DAY-05"].expected_behavior == "abstenerse"


def test_exporta_corpus_banco_e_informe_de_forma_reproducible(
    tmp_path: Path,
) -> None:
    from export_jurisprudence_sample_evaluation import (
        export_sample_evaluation,
    )

    kwargs = {
        "manifest_path": MANIFEST_PATH,
        "pilot_path": PILOT_PATH,
        "retrieval_root": RETRIEVAL_ROOT,
        "output_root": tmp_path,
        "project_root": PROJECT_ROOT,
        "sample_build_path": SAMPLE_BUILD_PATH,
    }
    first = export_sample_evaluation(**kwargs)
    first_payloads = tuple(path.read_bytes() for path in first.artifact_paths)
    second = export_sample_evaluation(**kwargs)

    assert first_payloads == tuple(path.read_bytes() for path in second.artifact_paths)
    assert second.question_count == 40
    assert second.expected_recall_at_12 == 1
    assert second.chat_behavior_gate == "NOT_EVALUATED"


@pytest.mark.parametrize(
    ("field_path", "replacement", "error"),
    [
        (("judgment", "judgment_id"), "san-1136-2016", "judgment_id"),
        (("source", "source_sha256"), "f" * 64, "source_sha256"),
        (("source", "case_sha256"), "f" * 64, "case_sha256"),
    ],
)
def test_rechaza_indices_que_no_corresponden_al_manifiesto_y_build(
    tmp_path: Path,
    field_path: tuple[str, str],
    replacement: str,
    error: str,
) -> None:
    from export_jurisprudence_sample_evaluation import export_sample_evaluation

    retrieval_root = tmp_path / "retrieval"
    shutil.copytree(RETRIEVAL_ROOT, retrieval_root)
    index_path = retrieval_root / "san-1071-2025.issues.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index[field_path[0]][field_path[1]] = replacement
    index_path.write_text(json.dumps(index), encoding="utf-8")

    with pytest.raises(ValueError, match=error):
        export_sample_evaluation(
            manifest_path=MANIFEST_PATH,
            pilot_path=PILOT_PATH,
            retrieval_root=retrieval_root,
            output_root=tmp_path / "output",
            project_root=PROJECT_ROOT,
            sample_build_path=SAMPLE_BUILD_PATH,
        )


def test_rechaza_un_indice_modificado_despues_del_sample_build(
    tmp_path: Path,
) -> None:
    from export_jurisprudence_sample_evaluation import export_sample_evaluation

    retrieval_root = tmp_path / "retrieval"
    shutil.copytree(RETRIEVAL_ROOT, retrieval_root)
    index_path = retrieval_root / "san-1071-2025.issues.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["units"][0]["search_text"] += "\ncontenido alterado"
    index_path.write_text(json.dumps(index), encoding="utf-8")

    with pytest.raises(ValueError, match="retrieval_sha256"):
        export_sample_evaluation(
            manifest_path=MANIFEST_PATH,
            pilot_path=PILOT_PATH,
            retrieval_root=retrieval_root,
            output_root=tmp_path / "output",
            project_root=PROJECT_ROOT,
            sample_build_path=SAMPLE_BUILD_PATH,
        )
