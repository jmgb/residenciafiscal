from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_chat_legal_review_validation import _completed_review


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    review = tmp_path / "review.md"
    package = tmp_path / "package.json"
    reveal = tmp_path / "reveal.json"
    review.write_text(_completed_review(), encoding="utf-8")
    common = {
        "rubric_version": "rubric/1",
        "rubric_sha256": "a" * 64,
        "dev_set_sha256": "b" * 64,
    }
    package.write_text(
        json.dumps(
            {
                **common,
                "questions": [{"question_id": "Q1"}],
            }
        ),
        encoding="utf-8",
    )
    reveal.write_text(
        json.dumps(
            {
                **common,
                "questions": [
                    {
                        "question_id": "Q1",
                        "x_strategy": "current_structured",
                        "y_strategy": "gemini_file_search",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return review, package, reveal


def test_compilador_exige_confirmacion_antes_de_abrir_la_clave(tmp_path: Path) -> None:
    from chat_legal_review_results import compile_review_results

    review, package, reveal = _inputs(tmp_path)

    with pytest.raises(ValueError, match="confirmación explícita"):
        compile_review_results(
            review_path=review,
            package_path=package,
            reveal_key_path=reveal,
            output_json=tmp_path / "results.json",
            output_markdown=tmp_path / "results.md",
            confirm_reveal=False,
            review_commit="abc1234",
        )


def test_compilador_revela_estrategias_y_calcula_metricas(tmp_path: Path) -> None:
    from chat_legal_review_results import compile_review_results

    review, package, reveal = _inputs(tmp_path)
    original_review = review.read_bytes()
    output_json = tmp_path / "results.json"
    output_markdown = tmp_path / "results.md"

    result = compile_review_results(
        review_path=review,
        package_path=package,
        reveal_key_path=reveal,
        output_json=output_json,
        output_markdown=output_markdown,
        confirm_reveal=True,
        review_commit="abc1234",
    )

    assert review.read_bytes() == original_review
    assert result["review_commit"] == "abc1234"
    assert result["questions"][0]["responses"][0] == {
        "label": "X",
        "strategy": "current_structured",
        "safe": True,
        "useful": True,
        "mean_score": 1.83,
        "critical_error": False,
        "gates": {"G1": "pasa", "G2": "pasa", "G3": "pasa", "G4": "pasa", "G5": "pasa"},
        "scores": {
            "Fidelidad jurídica": 2,
            "Relevancia para la pregunta": 2,
            "Respaldo de fuentes": 2,
            "Cobertura y contraste": 1,
            "Calibración y límites": 2,
            "Claridad y utilidad": 2,
        },
    }
    assert result["questions"][0]["preferred_strategy"] == "current_structured"
    assert result["aggregates"]["current_structured"]["preferred_count"] == 1
    assert result["aggregates"]["gemini_file_search"]["preferred_count"] == 0
    assert json.loads(output_json.read_bytes()) == result
    assert "current_structured" in output_markdown.read_text(encoding="utf-8")


def test_compilador_rechaza_revision_incompleta_y_clave_incompatible(tmp_path: Path) -> None:
    from chat_legal_review_results import compile_review_results

    review, package, reveal = _inputs(tmp_path)
    review.write_text(
        _completed_review().replace("- Fecha de cierre: 2026-08-02", ""),
        encoding="utf-8",
    )

    def compile_test_inputs() -> dict[str, object]:
        return compile_review_results(
            review_path=review,
            package_path=package,
            reveal_key_path=reveal,
            output_json=tmp_path / "results.json",
            output_markdown=tmp_path / "results.md",
            confirm_reveal=True,
            review_commit="abc1234",
        )

    with pytest.raises(ValueError, match="incompleta"):
        compile_test_inputs()

    review.write_text(_completed_review(), encoding="utf-8")
    key = json.loads(reveal.read_bytes())
    key["rubric_sha256"] = "c" * 64
    reveal.write_text(json.dumps(key), encoding="utf-8")
    with pytest.raises(ValueError, match="no coincide"):
        compile_test_inputs()
