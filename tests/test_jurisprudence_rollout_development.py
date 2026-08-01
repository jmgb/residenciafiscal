"""Banco de desarrollo y diagnóstico de cobertura separados del holdout."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "sentencias/jurisprudence_v3_rollout_106.json"
OUTPUT_ROOT = PROJECT_ROOT / "knowledge/jurisprudencia-v3"
HOLDOUT_PATH = PROJECT_ROOT / "docs/experiments/CHAT_QUESTION_HOLDOUT_E.json"


def test_banco_de_desarrollo_cubre_los_casos_recuperables_sin_usar_el_holdout() -> None:
    from jurisprudence_rollout_development import build_rollout_development_bank

    bank = build_rollout_development_bank(
        manifest_path=MANIFEST_PATH,
        output_root=OUTPUT_ROOT,
        project_root=PROJECT_ROOT,
    )

    assert len(bank.questions) == 117
    assert bank.source_resource == "sentencias/jurisprudence_v3_rollout_106.json"
    assert not {item.question_id for item in bank.questions} & {
        item["question_id"]
        for item in __import__("json").loads(HOLDOUT_PATH.read_text(encoding="utf-8"))["questions"]
    }
    assert all(item.behavior == "responder" for item in bank.questions)


def test_evaluacion_de_desarrollo_mide_baseline_y_candidato_sin_holdout() -> None:
    from jurisprudence_retrieval_corpus import load_retrieval_corpus
    from jurisprudence_rollout_development import (
        build_rollout_development_bank,
        evaluate_rollout_development,
    )

    bank = build_rollout_development_bank(
        manifest_path=MANIFEST_PATH,
        output_root=OUTPUT_ROOT,
        project_root=PROJECT_ROOT,
    )
    corpus = load_retrieval_corpus((OUTPUT_ROOT / "retrieval/rollout-106.corpus.json").read_bytes())

    report = evaluate_rollout_development(bank=bank, corpus=corpus)

    assert report.schema_version == "residenciafiscal-rollout-development/1"
    assert report.evaluation_policy == "DEVELOPMENT_ONLY_HOLDOUT_EXCLUDED"
    assert report.question_count == 117
    assert report.candidate_top_1_accuracy >= 0.95
    assert report.candidate_expected_recall_at_3 >= report.baseline_expected_recall_at_3
    assert report.gate_status == "PASSED"


def test_declara_incompleta_la_cobertura_del_holdout_historico_sobre_106() -> None:
    from jurisprudence_holdout_coverage import assess_holdout_coverage
    from jurisprudence_retrieval_corpus import load_retrieval_corpus
    from jurisprudence_sample_evaluation_models import RetrievalEvaluationBank

    bank = RetrievalEvaluationBank.model_validate_json(HOLDOUT_PATH.read_bytes())
    corpus = load_retrieval_corpus((OUTPUT_ROOT / "retrieval/rollout-106.corpus.json").read_bytes())

    assessment = assess_holdout_coverage(bank=bank, corpus=corpus)

    assert assessment.status == "LEGACY_LABELS_INCOMPLETE"
    assert assessment.corpus_source_count == 106
    assert assessment.annotated_source_count == 5
    assert assessment.unannotated_source_count == 101
    assert assessment.full_corpus_precision_is_valid is False
