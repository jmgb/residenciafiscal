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

    async def answer(self, question: str, *, request_id: str) -> Any:
        return self.result


class FailingStrategy:
    async def answer(self, question: str, *, request_id: str) -> Any:
        raise RuntimeError("fallo aislado")


async def test_comparador_ejecuta_ambas_estrategias_independientes_y_en_orden(
    tmp_path: Path,
) -> None:
    from chat_strategy_comparison import compare_strategies

    destination = tmp_path / "comparison.json"
    report = await compare_strategies(
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


async def test_un_fallo_no_impide_ejecutar_y_conservar_la_otra_estrategia(
    tmp_path: Path,
) -> None:
    from chat_strategy_comparison import compare_strategies

    report = await compare_strategies(
        question="Pregunta",
        structured=FailingStrategy(),
        file_search=FakeStrategy(_answer("gemini_file_search", "Respuesta B")),
        output_path=tmp_path / "comparison.json",
        log_path=tmp_path / "comparison.jsonl",
        request_id="req-error",
    )

    assert report.answers[0].strategy == "current_structured"
    assert report.answers[0].status == "error"
    assert report.answers[0].cost.measurement == "UNAVAILABLE"
    assert report.answers[1].text == "Respuesta B"
    serialized = (tmp_path / "comparison.json").read_text(encoding="utf-8")
    assert "fallo aislado" not in serialized
