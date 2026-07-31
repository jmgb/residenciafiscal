"""Sentry configuration for the FastAPI service."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event


def before_send(event: Event, _hint: dict[str, Any]) -> Event:
    """Remove request secrets and attach stable service metadata."""
    request = event.get("request")
    if request is not None:
        request.pop("headers", None)
        request.pop("cookies", None)
        request.pop("data", None)

    tags = event.setdefault("tags", {})
    tags["service"] = "residencia-fiscal"
    tags["component"] = "fastapi"
    return event


def running_under_pytest() -> bool:
    """Detect a pytest session, including at import time.

    `PYTEST_VERSION` lo publica pytest durante toda la sesión, también mientras
    recolecta; `PYTEST_CURRENT_TEST` no sirve porque solo existe dentro de cada
    test, y `api.main` se importa antes. `sys.modules` cubre pytest anteriores
    a la 8.0.
    """
    return "PYTEST_VERSION" in os.environ or "pytest" in sys.modules


def init_sentry() -> bool:
    """Initialize Sentry when explicitly enabled and a backend DSN is present."""
    # La suite provoca excepciones a propósito (fail-closed del chat, fallos de
    # estrategia) y no debe ensuciar el Sentry real con ellas: aquí no se
    # instrumenta aunque el `.env` local tenga la telemetría encendida.
    if running_under_pytest():
        return False

    enabled = os.getenv("SENTRY_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    dsn = os.getenv("SENTRY_BACKEND_DSN", "").strip()
    if not enabled or not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "development").strip(),
        release=os.getenv("SENTRY_RELEASE", "").strip() or None,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
        include_local_variables=False,
        attach_stacktrace=True,
        max_breadcrumbs=50,
        before_send=before_send,
    )
    return True
