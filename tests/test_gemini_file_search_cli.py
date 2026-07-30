from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def test_interactions_api_usa_sdk_google_genai_2_o_superior() -> None:
    sdk_major = int(version("google-genai").split(".", maxsplit=1)[0])

    assert sdk_major >= 2


def test_prepare_store_exige_confirmacion_explicita_antes_de_facturar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gemini_file_search_cli import main

    monkeypatch.setenv("GEMINI_API_KEY", "would-spend-money")

    with pytest.raises(SystemExit, match="--confirm-paid"):
        main(["prepare-store"])


def test_compare_exige_confirmacion_explicita_antes_de_facturar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gemini_file_search_cli import main

    monkeypatch.setenv("GEMINI_API_KEY", "would-spend-money")

    with pytest.raises(SystemExit, match="--confirm-paid"):
        main(["compare", "¿Qué resolvió la Sala?"])


def test_modelo_inicial_y_promocion_manual_estan_en_la_allowlist() -> None:
    from chat_strategy_costs import (
        DEFAULT_FILE_SEARCH_MODEL,
        SUPPORTED_FILE_SEARCH_MODELS,
    )

    assert DEFAULT_FILE_SEARCH_MODEL == "gemini-3.5-flash-lite"
    assert SUPPORTED_FILE_SEARCH_MODELS == (
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
    )


def test_compare_entrega_el_mismo_modelo_a_los_dos_redactores(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import gemini_file_search_cli

    gateway = object()
    shared_llm_gateway = object()
    corpus = SimpleNamespace(units=[])
    captured: dict[str, Any] = {}
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_bytes(b"{}")

    async def fake_compare_strategies(**kwargs: Any) -> Any:
        captured.update(kwargs)
        answer = SimpleNamespace(
            strategy="current_structured",
            status="completa",
            cost=SimpleNamespace(amount_usd="0.000001", measurement="ACTUAL"),
        )
        return SimpleNamespace(answers=[answer, answer])

    monkeypatch.setattr(gemini_file_search_cli, "_api_key", lambda: "fake-key")
    monkeypatch.setattr(
        gemini_file_search_cli,
        "_load_store",
        lambda _: SimpleNamespace(store_name="stores/f0", documents=[]),
    )
    monkeypatch.setattr(
        gemini_file_search_cli,
        "load_retrieval_corpus",
        lambda _: corpus,
    )
    monkeypatch.setattr(
        gemini_file_search_cli,
        "get_gateway",
        lambda: shared_llm_gateway,
    )
    monkeypatch.setattr(
        gemini_file_search_cli,
        "create_google_genai_gateway",
        lambda _: gateway,
    )
    monkeypatch.setattr(
        gemini_file_search_cli,
        "compare_strategies",
        fake_compare_strategies,
    )

    result = gemini_file_search_cli.main(
        [
            "compare",
            "Pregunta",
            "--state",
            str(tmp_path / "state.json"),
            "--corpus",
            str(corpus_path),
            "--output",
            str(tmp_path / "result.json"),
            "--model",
            "gemini-3.6-flash",
            "--confirm-paid",
        ]
    )

    assert result == 0
    from gateway_chat_writer import GatewayChatWriter

    assert isinstance(captured["structured"]._writer, GatewayChatWriter)
    assert captured["structured"]._writer._gateway is shared_llm_gateway
    assert captured["structured"]._model == "gemini-3.6-flash"
    assert captured["file_search"]._gateway is gateway
    assert captured["file_search"]._model == "gemini-3.6-flash"
