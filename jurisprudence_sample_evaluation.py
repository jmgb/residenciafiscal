"""Parser del piloto humano y evaluación del corpus agregado."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from jurisprudence_retrieval_corpus import RetrievalHit, rank_retrieval_units
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from jurisprudence_sample_evaluation_models import (
    RetrievalEvaluationBank,
    RetrievalEvaluationQuestion,
    RetrievalEvaluationReport,
    RetrievalEvaluationResult,
)

_HEADING = re.compile(
    r"^#### \d+\. `(?P<id>[A-Z]+-\d+)` — (?P<question>.+)$",
    re.MULTILINE,
)
_CASE_ID = re.compile(r"`(1071|1136|1210|1226|1386)`")
_JUDGMENTS = {
    "1071": "san-1071-2025",
    "1136": "san-1136-2016",
    "1210": "san-1210-2023",
    "1226": "san-1226-2021",
    "1386": "san-1386-2017",
}


def _behavior(block: str) -> str:
    match = re.search(r"- \*\*Conducta:\*\* `([^`]+)`", block)
    if match is None:
        raise ValueError("pregunta sin Conducta")
    value = match.group(1)
    for behavior in ("abstenerse", "preguntar", "parcial", "responder"):
        if value.startswith(behavior):
            return behavior
    raise ValueError(f"Conducta no reconocida: {value}")


def _case_annotation(block: str) -> str:
    match = re.search(
        r"- \*\*Casos esperados(?: / contraste)?:\*\* (?P<value>.*?)(?=\n- \*\*|\Z)",
        block,
        re.DOTALL,
    )
    if match is None:
        raise ValueError("pregunta sin Casos esperados")
    return " ".join(line.strip() for line in match.group("value").splitlines())


def _case_ids(text: str) -> tuple[str, ...]:
    return tuple(_JUDGMENTS[item] for item in _CASE_ID.findall(text))


def _expected_and_contrast(annotation: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if annotation.startswith("Todos"):
        return tuple(_JUDGMENTS.values()), ()
    if annotation.startswith("Dependen"):
        return (), ()
    if "↔" in annotation:
        return _case_ids(annotation), ()
    if " / " in annotation:
        expected, contrast = annotation.split(" / ", maxsplit=1)
        return _case_ids(expected), _case_ids(contrast)
    if ";" in annotation and ("como contraste" in annotation or "como límite" in annotation):
        expected, contrast = annotation.split(";", maxsplit=1)
        return _case_ids(expected), _case_ids(contrast)
    return _case_ids(annotation), ()


def parse_question_pilot(path: Path) -> RetrievalEvaluationBank:
    """Convierte el Markdown humano en un banco estricto, sin duplicarlo a mano."""

    markdown = path.read_text(encoding="utf-8")
    headings = tuple(_HEADING.finditer(markdown))
    questions = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown)
        block = markdown[heading.end() : end]
        expected, contrast = _expected_and_contrast(_case_annotation(block))
        questions.append(
            RetrievalEvaluationQuestion(
                question_id=heading.group("id"),
                question=heading.group("question"),
                behavior=_behavior(block),
                expected_judgment_ids=expected,
                contrast_judgment_ids=contrast,
            )
        )
    ids = tuple(item.question_id for item in questions)
    if len(ids) != len(set(ids)):
        raise ValueError("el piloto contiene question_id duplicado")
    return RetrievalEvaluationBank(
        schema_version="residenciafiscal-retrieval-evaluation-bank/1",
        source_resource=path.as_posix(),
        questions=tuple(questions),
    )


def _recall(expected: tuple[str, ...], retrieved: tuple[str, ...]) -> float | None:
    if not expected:
        return None
    return len(set(expected) & set(retrieved)) / len(set(expected))


def _judgments(unit_hits: tuple[RetrievalHit, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.judgment_id for item in unit_hits))


def _mean(values: tuple[float | None, ...]) -> float:
    measured = tuple(item for item in values if item is not None)
    return sum(measured) / len(measured) if measured else 1.0


def evaluate_question_bank(
    bank: RetrievalEvaluationBank,
    corpus: RetrievalCorpus,
) -> RetrievalEvaluationReport:
    """Ejecuta las preguntas y conserva ranking y recall por caso."""

    results = []
    for question in bank.questions:
        top_12 = rank_retrieval_units(corpus, question.question, limit=12)
        top_5 = top_12[:5]
        judgments_5 = _judgments(top_5)
        judgments_12 = _judgments(top_12)
        results.append(
            RetrievalEvaluationResult(
                question_id=question.question_id,
                expected_behavior=question.behavior,
                expected_judgment_ids=question.expected_judgment_ids,
                contrast_judgment_ids=question.contrast_judgment_ids,
                retrieved_unit_ids_at_5=tuple(item.unit_id for item in top_5),
                retrieved_unit_ids_at_12=tuple(item.unit_id for item in top_12),
                retrieved_judgment_ids_at_5=judgments_5,
                retrieved_judgment_ids_at_12=judgments_12,
                expected_recall_at_5=_recall(
                    question.expected_judgment_ids,
                    judgments_5,
                ),
                expected_recall_at_12=_recall(
                    question.expected_judgment_ids,
                    judgments_12,
                ),
                contrast_recall_at_5=_recall(
                    question.contrast_judgment_ids,
                    judgments_5,
                ),
                contrast_recall_at_12=_recall(
                    question.contrast_judgment_ids,
                    judgments_12,
                ),
            )
        )
    result_tuple = tuple(results)
    behavior_counts = Counter(item.behavior for item in bank.questions)
    return RetrievalEvaluationReport(
        schema_version="residenciafiscal-retrieval-evaluation-report/2",
        sample_id=corpus.sample_id,
        evaluation_scope="RETRIEVAL_ONLY",
        chat_behavior_gate="NOT_EVALUATED",
        question_count=len(result_tuple),
        expected_behavior_counts=dict(sorted(behavior_counts.items())),
        expected_recall_at_5=_mean(tuple(item.expected_recall_at_5 for item in result_tuple)),
        expected_recall_at_12=_mean(tuple(item.expected_recall_at_12 for item in result_tuple)),
        contrast_recall_at_5=_mean(tuple(item.contrast_recall_at_5 for item in result_tuple)),
        contrast_recall_at_12=_mean(tuple(item.contrast_recall_at_12 for item in result_tuple)),
        results=result_tuple,
    )


def render_evaluation_bank(bank: RetrievalEvaluationBank) -> str:
    return (
        json.dumps(
            bank.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def render_evaluation_report(report: RetrievalEvaluationReport) -> str:
    return (
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
