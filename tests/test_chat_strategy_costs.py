from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


def test_coste_gemini_37_flash_usa_su_tarifa_versionada() -> None:
    from chat_strategy_costs import PRICING_VERSION, GeminiUsage, calculate_gemini_file_search_cost

    cost = calculate_gemini_file_search_cost(
        GeminiUsage(
            input_tokens=3_321,
            retrieved_document_tokens=5_100,
            output_tokens=631,
            usage_complete=True,
        ),
        model="gemini-3.8-flash",
    )

    assert cost.currency == "USD"
    assert cost.amount_usd == Decimal("0.008682")
    assert cost.cost_microusd == 8_682
    assert cost.measurement == "ACTUAL"
    assert cost.pricing_version == PRICING_VERSION
    assert cost.input_tokens == 3_321
    assert cost.retrieved_document_tokens == 5_100
    assert cost.output_tokens == 631


def test_modelo_inicial_35_flash_lite_usa_su_tarifa_menor() -> None:
    from chat_strategy_costs import (
        DEFAULT_FILE_SEARCH_MODEL,
        GeminiUsage,
        calculate_gemini_file_search_cost,
    )

    cost = calculate_gemini_file_search_cost(
        GeminiUsage(
            input_tokens=3_321,
            retrieved_document_tokens=5_100,
            output_tokens=631,
            usage_complete=True,
        )
    )

    assert DEFAULT_FILE_SEARCH_MODEL == "gemini-3.5-flash-lite"
    assert cost.amount_usd == Decimal("0.004104")
    assert cost.cost_microusd == 4_104


def test_coste_es_estimado_si_el_proveedor_no_desglosa_documentos() -> None:
    from chat_strategy_costs import GeminiUsage, calculate_gemini_file_search_cost

    cost = calculate_gemini_file_search_cost(
        GeminiUsage(
            input_tokens=100,
            retrieved_document_tokens=0,
            output_tokens=20,
            usage_complete=False,
        )
    )

    assert cost.measurement == "ESTIMATED"
    assert cost.amount_usd == Decimal("0.000080")


def test_log_jsonl_no_contiene_pregunta_ni_respuesta(tmp_path: Path) -> None:
    from chat_strategy_costs import PRICING_VERSION, GeminiUsage, calculate_gemini_file_search_cost
    from chat_strategy_logging import StrategyLogRecord, append_strategy_log

    destination = tmp_path / "comparison.jsonl"
    record = StrategyLogRecord(
        request_id="req-123",
        strategy="gemini_file_search",
        status="ok",
        cost=calculate_gemini_file_search_cost(
            GeminiUsage(
                input_tokens=100,
                retrieved_document_tokens=20,
                output_tokens=10,
                usage_complete=True,
            )
        ),
        model="gemini-3.5-flash-lite",
        latency_ms=2840,
    )

    append_strategy_log(destination, record)

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload == {
        "request_id": "req-123",
        "strategy": "gemini_file_search",
        "status": "ok",
        "cost_microusd": 61,
        "cost_measurement": "ACTUAL",
        "pricing_version": PRICING_VERSION,
        "model": "gemini-3.5-flash-lite",
        "input_tokens": 100,
        "retrieved_document_tokens": 20,
        "output_tokens": 10,
        "latency_ms": 2840,
    }
    assert "question" not in payload
    assert "answer" not in payload
