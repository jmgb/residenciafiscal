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
        "gemini-3.8-flash",
    )


def test_defaults_productivos_apuntan_al_rollout_de_106() -> None:
    from gemini_file_search_cli import (
        DEFAULT_CORPUS,
        DEFAULT_MANIFEST,
        DEFAULT_STORE_STATE,
    )

    assert DEFAULT_MANIFEST.name == "jurisprudence_v3_rollout_106.json"
    assert DEFAULT_CORPUS.name == "rollout-106.corpus.json"
    assert DEFAULT_STORE_STATE.name == "rollout-106-store.json"


def test_compare_da_a_cada_estrategia_el_modelo_que_le_corresponde(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import gemini_file_search_cli

    gateway = object()
    shared_llm_gateway = object()
    corpus = SimpleNamespace(units=[], sources=[])
    captured: dict[str, Any] = {}
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_bytes(b"{}")

    async def fake_compare_strategies(**kwargs: Any) -> Any:
        captured.update(kwargs)
        answer = SimpleNamespace(
            strategy="current_structured",
            status="completa",
            cost=SimpleNamespace(amount_usd="0.000001", measurement="ACTUAL"),
            claims=(),
            sources=(),
            limits=(),
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
            "gemini-3.8-flash",
            "--chat-model",
            "gpt-5.6-luna",
            "--chat-fallback-model",
            "gemini-3.8-flash",
            "--confirm-paid",
        ]
    )

    assert result == 0
    from chat_model_policy import CHAT_REASONING_EFFORT
    from gateway_chat_writer import GatewayChatWriter

    assert isinstance(captured["structured"]._writer, GatewayChatWriter)
    assert captured["structured"]._writer._gateway is shared_llm_gateway

    # `--model` gobierna solo a B. File Search es una capacidad de Gemini, así
    # que B no puede correr sobre otro proveedor; atar A a esa restricción era
    # lo que dejaba la política del chat sin llegar a ninguna llamada.
    assert captured["file_search"]._gateway is gateway
    assert captured["file_search"]._model == "gemini-3.8-flash"

    assert captured["structured"]._model == "gpt-5.6-luna"
    assert captured["structured"]._reasoning_effort == CHAT_REASONING_EFFORT
    assert captured["structured"]._fallback_models == ("gemini-3.8-flash",)
    assert captured["structured"]._model != captured["file_search"]._model
