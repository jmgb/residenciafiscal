"""Evaluación reproducible del router y recuperación estructurada de fase D."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from jurisprudence_phase_d_evaluation_models import (
    BehaviorMetrics,
    EvaluationInputs,
    ParaphraseDefinitions,
    PhaseDEvaluationReport,
    PhaseDQuestionResult,
    StrategyMetrics,
)
from jurisprudence_phase_d_retrieval import retrieve_for_chat
from jurisprudence_retrieval_corpus import rank_retrieval_units
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from jurisprudence_sample_evaluation_models import (
    RetrievalEvaluationBank,
    RetrievalEvaluationQuestion,
)


def load_paraphrase_bank(path: Path) -> ParaphraseDefinitions:
    definitions = ParaphraseDefinitions.model_validate_json(path.read_bytes())
    ids = tuple(item.question_id for item in definitions.questions)
    if len(ids) != len(set(ids)):
        raise ValueError("el banco de paráfrasis contiene question_id duplicado")
    return definitions


def materialize_paraphrase_bank(
    definitions: ParaphraseDefinitions,
    source: RetrievalEvaluationBank,
) -> RetrievalEvaluationBank:
    """Hereda anotaciones sin copiarlas al fichero de consultas ciegas."""

    source_by_id = {item.question_id: item for item in source.questions}
    questions = []
    for definition in definitions.questions:
        if definition.source_question_id not in source_by_id:
            raise ValueError(f"source_question_id desconocido: {definition.source_question_id}")
        gold = source_by_id[definition.source_question_id]
        questions.append(
            RetrievalEvaluationQuestion(
                question_id=definition.question_id,
                question=definition.question,
                behavior=gold.behavior,
                expected_judgment_ids=gold.expected_judgment_ids,
                contrast_judgment_ids=gold.contrast_judgment_ids,
            )
        )
    return RetrievalEvaluationBank(
        schema_version="residenciafiscal-retrieval-evaluation-bank/1",
        source_resource="docs/experiments/CHAT_QUESTION_PARAPHRASES_5.json",
        questions=tuple(questions),
    )


def _recall(expected: tuple[str, ...], retrieved: tuple[str, ...]) -> float | None:
    if not expected:
        return None
    return len(set(expected) & set(retrieved)) / len(set(expected))


def _mean(values: Sequence[float | None]) -> float:
    measured = [item for item in values if item is not None]
    return sum(measured) / len(measured) if measured else 1.0


def _model_sha256(model) -> str:
    payload = json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _strategy_metrics(
    rows: list[tuple[RetrievalEvaluationQuestion, tuple[str, ...]]],
) -> StrategyMetrics:
    expected_recalls = []
    precisions = []
    contrast_recalls = []
    for question, retrieved in rows:
        expected_recalls.append(_recall(question.expected_judgment_ids, retrieved))
        contrast_recalls.append(_recall(question.contrast_judgment_ids, retrieved))
        relevant = set(question.expected_judgment_ids) | set(question.contrast_judgment_ids)
        if relevant and retrieved:
            precisions.append(len(relevant & set(retrieved)) / len(set(retrieved)))
    return StrategyMetrics(
        measured_question_count=len(rows),
        expected_recall_at_3=_mean(expected_recalls),
        relevant_case_precision_at_3=_mean(precisions),
        contrast_recall_at_3=_mean(contrast_recalls),
    )


def _evaluate_bank(
    bank: RetrievalEvaluationBank,
    corpus: RetrievalCorpus,
) -> tuple[BehaviorMetrics, tuple[PhaseDQuestionResult, ...]]:
    results = []
    safe_expected = 0
    safe_correct = 0
    predicted: Counter[str] = Counter()
    for question in bank.questions:
        outcome = retrieve_for_chat(corpus, question.question, limit=3)
        retrieved = tuple(hit.judgment_id for hit in outcome.hits)
        predicted[outcome.behavior] += 1
        if question.behavior in {"preguntar", "abstenerse"}:
            safe_expected += 1
            safe_correct += not retrieved
        results.append(
            PhaseDQuestionResult(
                question_id=question.question_id,
                expected_behavior=question.behavior,
                predicted_behavior=outcome.behavior,
                retrieved_judgment_ids=retrieved,
                expected_recall_at_3=_recall(question.expected_judgment_ids, retrieved),
                contrast_recall_at_3=_recall(question.contrast_judgment_ids, retrieved),
            )
        )
    correct = sum(item.expected_behavior == item.predicted_behavior for item in results)
    metrics = BehaviorMetrics(
        question_count=len(results),
        behavior_accuracy=correct / len(results),
        zero_source_safety=safe_correct / safe_expected if safe_expected else 1,
        predicted_behavior_counts=dict(sorted(predicted.items())),
    )
    return metrics, tuple(results)


def evaluate_phase_d(
    *,
    corpus: RetrievalCorpus,
    original_bank: RetrievalEvaluationBank,
    paraphrase_bank: RetrievalEvaluationBank,
) -> PhaseDEvaluationReport:
    """Compara el baseline léxico y el candidato sin filtrar por gold."""

    original_metrics, original_results = _evaluate_bank(original_bank, corpus)
    paraphrase_metrics, paraphrase_results = _evaluate_bank(paraphrase_bank, corpus)
    answerable = tuple(
        item
        for item in (*original_bank.questions, *paraphrase_bank.questions)
        if item.behavior in {"responder", "parcial"}
    )
    baseline_rows = []
    candidate_rows = []
    for question in answerable:
        raw = rank_retrieval_units(corpus, question.question, limit=3)
        baseline_rows.append((question, tuple(dict.fromkeys(hit.judgment_id for hit in raw))))
        candidate_result = retrieve_for_chat(corpus, question.question, limit=3)
        candidate_rows.append((question, tuple(hit.judgment_id for hit in candidate_result.hits)))
    baseline = _strategy_metrics(baseline_rows)
    candidate = _strategy_metrics(candidate_rows)
    failures = []
    if original_metrics.behavior_accuracy < 0.90:
        failures.append("original.behavior_accuracy < 0.90")
    if paraphrase_metrics.behavior_accuracy < 0.80:
        failures.append("paraphrases.behavior_accuracy < 0.80")
    if min(original_metrics.zero_source_safety, paraphrase_metrics.zero_source_safety) < 1:
        failures.append("zero_source_safety < 1")
    if candidate.expected_recall_at_3 < baseline.expected_recall_at_3:
        failures.append("candidate.expected_recall_at_3 < baseline")
    if candidate.contrast_recall_at_3 < 0.80:
        failures.append("candidate.contrast_recall_at_3 < 0.80")
    return PhaseDEvaluationReport(
        schema_version="residenciafiscal-phase-d-evaluation/1",
        sample_id=corpus.sample_id,
        evaluation_policy="GOLD_USED_ONLY_AFTER_RETRIEVAL",
        inputs=EvaluationInputs(
            corpus_sha256=_model_sha256(corpus),
            original_bank_sha256=_model_sha256(original_bank),
            paraphrase_bank_sha256=_model_sha256(paraphrase_bank),
        ),
        original=original_metrics,
        paraphrases=paraphrase_metrics,
        baseline=baseline,
        candidate=candidate,
        embedding_decision=("NOT_REQUIRED_FOR_PILOT" if not failures else "REQUIRES_EXPERIMENT"),
        gate_status="PASSED" if not failures else "FAILED",
        gate_failures=tuple(failures),
        original_results=original_results,
        paraphrase_results=paraphrase_results,
    )


def render_phase_d_report(report: PhaseDEvaluationReport) -> str:
    return (
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
