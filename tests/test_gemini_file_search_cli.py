from __future__ import annotations

import pytest


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
