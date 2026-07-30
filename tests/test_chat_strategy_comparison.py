from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any


def _answer(strategy: str, text: str) -> Any:
    from chat_strategy_models import MarginalCost, StrategyAnswer

    return StrategyAnswer(
        strategy=strategy,
        status="completa",
        text=text,
        sources=(),
        limits=(),
        cost=MarginalCost(
            amount_usd=Decimal("0"),
            cost_microusd=0,
            measurement="ACTUAL",
            pricing_version="2026-07-30",
            input_tokens=0,
            retrieved_document_tokens=0,
            output_tokens=0,
        ),
        model="deterministic",
        latency_ms=1,
    )


class FakeStrategy:
    def __init__(self, result: Any) -> None:
        self.result = result

    def answer(self, question: str, *, request_id: str) -> Any:
        return self.result


class FailingStrategy:
    def answer(self, question: str, *, request_id: str) -> Any:
        raise RuntimeError("fallo aislado")


def test_comparador_ejecuta_ambas_estrategias_independientes_y_en_orden(
    tmp_path: Path,
) -> None:
    from chat_strategy_comparison import compare_strategies

    destination = tmp_path / "comparison.json"
    report = compare_strategies(
        question="¿Qué prueba se valoró?",
        structured=FakeStrategy(_answer("current_structured", "Respuesta A")),
        file_search=FakeStrategy(_answer("gemini_file_search", "Respuesta B")),
        output_path=destination,
        log_path=tmp_path / "comparison.jsonl",
        request_id="req-same",
    )

    assert tuple(item.strategy for item in report.answers) == (
        "current_structured",
        "gemini_file_search",
    )
    assert report.answers[0].text == "Respuesta A"
    assert report.answers[1].text == "Respuesta B"
    serialized = json.loads(destination.read_text(encoding="utf-8"))
    assert "question" not in serialized
    assert serialized["request_id"] == "req-same"
    assert [item["strategy"] for item in serialized["answers"]] == [
        "current_structured",
        "gemini_file_search",
    ]
    assert len((tmp_path / "comparison.jsonl").read_text().splitlines()) == 2


def test_un_fallo_no_impide_ejecutar_y_conservar_la_otra_estrategia(
    tmp_path: Path,
) -> None:
    from chat_strategy_comparison import compare_strategies

    report = compare_strategies(
        question="Pregunta",
        structured=FailingStrategy(),
        file_search=FakeStrategy(_answer("gemini_file_search", "Respuesta B")),
        output_path=tmp_path / "comparison.json",
        log_path=tmp_path / "comparison.jsonl",
        request_id="req-error",
    )

    assert report.answers[0].strategy == "current_structured"
    assert report.answers[0].status == "error"
    assert report.answers[0].cost.measurement == "ESTIMATED"
    assert report.answers[1].text == "Respuesta B"


def test_estrategia_estructurada_renderiza_solo_hits_y_anclajes_actuales() -> None:
    from current_structured_strategy import CurrentStructuredStrategy
    from jurisprudence_retrieval_corpus import load_retrieval_corpus

    corpus = load_retrieval_corpus(
        Path("knowledge/jurisprudencia-v3/retrieval/corpus.json").read_bytes()
    )
    result = CurrentStructuredStrategy(corpus).answer(
        "¿Qué valor tienen el certificado fiscal extranjero y los consumos?",
        request_id="req-local",
    )

    assert result.strategy == "current_structured"
    assert result.status in {"completa", "parcial"}
    assert result.text
    assert result.sources
    assert all(source.verification == "EXACT" for source in result.sources)
    assert result.cost.amount_usd == Decimal("0")
