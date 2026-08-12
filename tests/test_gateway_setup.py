from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest


def test_gateway_dependency_esta_fijada_a_una_version_exacta() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencias = [
        dependencia
        for dependencia in pyproject["project"]["dependencies"]
        if dependencia.startswith("neutral-llm-gateway")
    ]

    assert dependencias == ["neutral-llm-gateway[gemini,groq,openai,openrouter]==0.13.0"]


def _clear_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import PROVIDER_API_KEY_ENV

    for variable in PROVIDER_API_KEY_ENV.values():
        monkeypatch.delenv(variable, raising=False)


def test_build_gateway_conecta_cliente_y_sinks_de_la_aplicacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from llm_gateway import ProviderRegistry

    import gateway_setup

    _clear_credentials(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "clave-gemini")
    client = object()
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        gateway_setup,
        "create_gemini_client",
        lambda *, api_key: client if api_key == "clave-gemini" else None,
    )

    def capture_registry(**clients: Any) -> ProviderRegistry:
        captured.update(clients)
        return ProviderRegistry()

    monkeypatch.setattr(gateway_setup, "build_registry", capture_registry)

    gateway = gateway_setup.build_gateway()

    assert captured == {"gemini_client": client}
    assert isinstance(gateway._usage_sink, gateway_setup.LoggingUsageSink)
    assert isinstance(gateway._alerts, gateway_setup.LoggingAlertSink)


def test_get_gateway_reutiliza_una_sola_instancia(monkeypatch: pytest.MonkeyPatch) -> None:
    import gateway_setup

    gateway_setup.reset_gateway()
    built = object()
    calls = 0

    def build_once() -> object:
        nonlocal calls
        calls += 1
        return built

    monkeypatch.setattr(gateway_setup, "build_gateway", build_once)

    assert gateway_setup.get_gateway() is built
    assert gateway_setup.get_gateway() is built
    assert calls == 1
    gateway_setup.reset_gateway()


def test_build_gateway_falla_antes_de_crear_un_registro_sin_credenciales(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gateway_setup

    _clear_credentials(monkeypatch)

    with pytest.raises(RuntimeError, match="No hay ninguna credencial"):
        gateway_setup.build_gateway()
