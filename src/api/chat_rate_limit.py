"""Límite autoritativo en memoria del servicio FastAPI.

La exactitud económica no se delega a Netlify Blobs, cuyo compare-and-swap
pierde incrementos bajo concurrencia. A cambio, este contador solo vale dentro
de un proceso: `require_single_process_state()` impide arrancar con varios
workers y una cuota que cada uno contaría por su cuenta. Escalar a más de un
proceso exige antes un contador transaccional en Supabase.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

WORKER_ENV_VARS = ("WEB_CONCURRENCY", "UVICORN_WORKERS", "GUNICORN_WORKERS")


class SlidingWindowRateLimiter:
    def __init__(
        self, *, limit: int = 5, window_seconds: int = 60, sweep_threshold: int = 1024
    ) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("el límite y la ventana deben ser positivos")
        self._limit = limit
        self._window_seconds = window_seconds
        self._sweep_threshold = sweep_threshold
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        cutoff = current - self._window_seconds
        with self._lock:
            # Un cliente que no vuelve nunca dejaría su clave viva para siempre:
            # purgar solo la clave tocada convierte el limitador en una fuga
            # proporcional al número de clientes vistos.
            if len(self._events) > self._sweep_threshold:
                self._sweep(cutoff)
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            allowed = len(events) < self._limit
            if allowed:
                events.append(current)
            if not events:
                del self._events[key]
            return allowed

    def _sweep(self, cutoff: float) -> None:
        expired = [
            key for key, events in self._events.items() if not events or events[-1] <= cutoff
        ]
        for key in expired:
            del self._events[key]

    @property
    def tracked_keys(self) -> int:
        with self._lock:
            return len(self._events)


chat_rate_limiter = SlidingWindowRateLimiter()


def configured_worker_count() -> int:
    for name in WORKER_ENV_VARS:
        value = os.getenv(name, "").strip()
        if value.isdigit():
            return int(value)
    return 1


def require_single_process_state() -> None:
    """Falla al arrancar si la cuota y el anti-replay quedarían repartidos."""
    workers = configured_worker_count()
    if workers > 1:
        raise RuntimeError(
            "la cuota y el anti-replay del chat viven en memoria de un proceso: "
            f"{workers} workers los harían inefectivos"
        )
