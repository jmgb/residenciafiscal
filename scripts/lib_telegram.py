"""Utilidades compartidas para los avisos operativos por Telegram.

`weekly_ga4_telegram.py` conserva de momento su propia copia de estas funciones:
está en producción desde hace semanas y su refactor merece un cambio propio con
su propio gate. Este módulo es el destino al que migrarlo cuando toque.

El `.env` se **parsea**, nunca se hace `source`: el mismo criterio que
`scripts/backup/lib-read-env.sh`.
"""

from __future__ import annotations

import json
import os
import pathlib
import urllib.request

try:
    import telegram_activity  # registro best-effort para el triage matinal
except Exception:  # sin registro no se bloquea el aviso
    telegram_activity = None  # type: ignore[assignment]

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]
ENV_PATHS = [PROJECT_DIR / ".env"]
TELEGRAM_TIMEOUT_SECONDS = 30


def load_env(paths: list[pathlib.Path] | None = None) -> dict[str, str]:
    """Lee pares `CLAVE=valor` sin ejecutar el fichero: nunca se hace `source`."""
    values: dict[str, str] = {}
    for path in paths if paths is not None else ENV_PATHS:
        if not path.exists():
            continue
        for raw_line in path.read_text(errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values.setdefault(key.strip(), value)
    return values


def env_value(env: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = os.environ.get(key) or env.get(key)
        if value:
            return value
    return ""


def send_telegram(message: str, env: dict[str, str]) -> None:
    token = env_value(env, "TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN", "TELEGRAM_TOKEN")
    chat_id = env_value(env, "TELEGRAM_CHAT_ID", "TG_CHAT_ID")
    thread_id = env_value(env, "TELEGRAM_MESSAGE_THREAD_ID", "TG_THREAD_ID")
    if not token:
        raise RuntimeError("Falta TELEGRAM_TOKEN en .env")
    if not chat_id:
        raise RuntimeError("Falta TELEGRAM_CHAT_ID en .env")

    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if thread_id:
        payload["message_thread_id"] = thread_id
    if telegram_activity:
        telegram_activity.registrar(message, referencia="lib_telegram")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TELEGRAM_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Telegram devolvió error: {body}")
