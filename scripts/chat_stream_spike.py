#!/usr/bin/env python3
"""Mide si un stream SSE largo sobrevive al proxy candidato (gate F0/D1).

El spike de 2026-07-29 llegó a 19,87 s por Edge Function; la migración necesita
90 s. Este cliente no despliega nada: consume el endpoint que se le indique y
reporta cabeceras, latidos y evento terminal, que es exactamente lo que decide
el gate. Ejecutarlo contra un Deploy Preview, nunca contra producción.

    uv run python scripts/chat_stream_spike.py <url> --repeat 3

No envía preguntas reales ni credenciales: el cuerpo es sintético y el endpoint
debe estar en modo spike. Si la respuesta trae eventos con contenido, el script
los cuenta pero no los imprime.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from typing import NamedTuple


class Measurement(NamedTuple):
    headers_seconds: float
    total_seconds: float
    protocol: str | None
    heartbeats: int
    events: int
    terminal: bool


SYNTHETIC_BODY = {
    "conversation_id": "conversation-spike",
    "country_path": "/espana",
    "messages": [{"id": "message-spike", "role": "user", "content": "spike sintético"}],
}


def _run_once(url: str, timeout: float) -> Measurement:
    started = time.monotonic()
    request = urllib.request.Request(  # noqa: S310 - URL la aporta el operador
        url,
        data=json.dumps(SYNTHETIC_BODY).encode(),
        headers={"content-type": "application/json", "accept": "text/event-stream"},
        method="POST",
    )
    heartbeats = 0
    events = 0
    terminal = False
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        headers_at = time.monotonic() - started
        protocol = response.headers.get("x-chat-protocol")
        for raw in response:
            line = raw.decode("utf-8", "replace")
            if line.startswith(": "):
                heartbeats += 1
            elif line.startswith("event: "):
                events += 1
                terminal = terminal or line.strip() == "event: done"
    return Measurement(
        headers_seconds=round(headers_at, 3),
        total_seconds=round(time.monotonic() - started, 3),
        protocol=protocol,
        heartbeats=heartbeats,
        events=events,
        terminal=terminal,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="endpoint del Deploy Preview, nunca producción")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--require-seconds",
        type=float,
        default=90.0,
        help="duración mínima que debe sobrevivir el stream para superar el gate",
    )
    args = parser.parse_args()

    results: list[Measurement] = []
    for attempt in range(1, args.repeat + 1):
        measurement = _run_once(args.url, args.timeout)
        results.append(measurement)
        print(f"intento {attempt}: {json.dumps(measurement._asdict(), ensure_ascii=False)}")

    completos = [
        item for item in results if item.terminal and item.total_seconds >= args.require_seconds
    ]
    print(f"streams completos de {args.require_seconds:.0f}s: {len(completos)}/{args.repeat}")
    return 0 if len(completos) == args.repeat else 1


if __name__ == "__main__":
    sys.exit(main())
