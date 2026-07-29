"""Cobertura del caso piloto sobre preguntas reales del chat."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = PROJECT_ROOT / "knowledge/jurisprudencia/cases/san-1210-2023.case.json"
EVALUATION_PATH = PROJECT_ROOT / "knowledge/jurisprudencia/evaluations/san-1210-2023.questions.json"


def test_preguntas_aplicables_quedan_ligadas_a_datos_y_citas() -> None:
    from jurisprudence_case_artifact import load_jurisprudence_case
    from jurisprudence_case_question_evaluation import (
        CaseQuestionEvaluation,
        validate_question_evaluation,
    )

    case = load_jurisprudence_case(CASE_PATH.read_bytes())
    evaluation = CaseQuestionEvaluation.model_validate_json(EVALUATION_PATH.read_bytes())

    result = validate_question_evaluation(evaluation, case)

    assert result.question_count == 18
    assert result.question_ids[0] == "GEN-01"
    assert result.question_ids[-1] == "SRC-02"


def test_rechaza_una_pregunta_con_referencia_inexistente() -> None:
    from jurisprudence_case_artifact import load_jurisprudence_case
    from jurisprudence_case_question_evaluation import (
        CaseQuestionEvaluation,
        validate_question_evaluation,
    )

    case = load_jurisprudence_case(CASE_PATH.read_bytes())
    raw = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    altered = deepcopy(raw)
    altered["questions"][0]["required_anchor_ids"] = ["anchor-inexistente"]
    evaluation = CaseQuestionEvaluation.model_validate(altered)

    with pytest.raises(ValueError, match="anchor-inexistente"):
        validate_question_evaluation(evaluation, case)
