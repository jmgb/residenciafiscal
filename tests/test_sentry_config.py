from __future__ import annotations

from typing import cast
from unittest.mock import Mock

import sentry_sdk
from sentry_sdk.types import Event

from api import sentry_config


def test_init_sentry_skips_when_disabled(monkeypatch) -> None:
    init = Mock()
    monkeypatch.setattr(sentry_config.sentry_sdk, "init", init)
    monkeypatch.setenv("SENTRY_ENABLED", "false")
    monkeypatch.setenv("SENTRY_BACKEND_DSN", "https://public@example.ingest.sentry.io/1")

    assert sentry_config.init_sentry() is False
    init.assert_not_called()


def test_init_sentry_skips_under_pytest(monkeypatch) -> None:
    # La suite nunca envía telemetría al Sentry real, aunque el `.env` del
    # desarrollador tenga la instrumentación activada para `make dev`.
    init = Mock()
    monkeypatch.setattr(sentry_config.sentry_sdk, "init", init)
    monkeypatch.setenv("SENTRY_ENABLED", "true")
    monkeypatch.setenv("SENTRY_BACKEND_DSN", "https://public@example.ingest.sentry.io/1")

    assert sentry_config.init_sentry() is False
    init.assert_not_called()


def test_init_sentry_uses_private_defaults(monkeypatch) -> None:
    init = Mock()
    monkeypatch.setattr(sentry_config.sentry_sdk, "init", init)
    monkeypatch.setattr(sentry_config, "running_under_pytest", lambda: False)
    monkeypatch.setenv("SENTRY_ENABLED", "true")
    monkeypatch.setenv("SENTRY_BACKEND_DSN", "https://public@example.ingest.sentry.io/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "production")
    monkeypatch.setenv("SENTRY_RELEASE", "residencia-fiscal-backend@test")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")

    assert sentry_config.init_sentry() is True

    options = init.call_args.kwargs
    assert options["dsn"] == "https://public@example.ingest.sentry.io/1"
    assert options["environment"] == "production"
    assert options["release"] == "residencia-fiscal-backend@test"
    assert options["traces_sample_rate"] == 0.25
    assert options["send_default_pii"] is False
    assert options["before_send"] is sentry_config.before_send


def test_before_send_removes_request_secrets_and_adds_service_tags() -> None:
    # `Event` es un TypedDict: el literal se castea porque aquí solo se rellenan
    # las claves que toca `before_send`, no el evento completo de Sentry.
    event = cast(
        Event,
        {
            "request": {
                "url": "https://api.example.test/analizar",
                "method": "POST",
                "headers": {"X-API-Token": "secret"},
                "cookies": "session=secret",
                "data": "pdf contents",
            }
        },
    )

    result = sentry_config.before_send(event, {})

    assert result is event
    assert result["request"] == {
        "url": "https://api.example.test/analizar",
        "method": "POST",
    }
    assert result["tags"] == {
        "service": "residencia-fiscal",
        "component": "fastapi",
    }


def test_importar_la_app_no_activa_telemetria_en_la_suite() -> None:
    # Regresión: `api.main` llama a `load_dotenv()` + `init_sentry()` al
    # importarse, así que un `.env` con `SENTRY_ENABLED=true` mandaba al Sentry
    # de producción cada excepción provocada a propósito por los tests.
    import api.main  # noqa: F401

    assert sentry_sdk.get_client().is_active() is False
