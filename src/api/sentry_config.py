"""Sentry configuration for the FastAPI service."""

from __future__ import annotations

import logging
import os
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


def init_sentry() -> bool:
    """Initialize Sentry when explicitly enabled and a backend DSN is present."""
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
