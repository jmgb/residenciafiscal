"""Resumen diario del ledger del chat a Telegram.

Lee agregados mediante la RPC `chat_daily_stats`, que devuelve exclusivamente
recuentos, sumas y percentiles: **nunca** la pregunta ni la respuesta. El script
no consulta tablas directamente, así que no puede leer contenido aunque quiera.

El coste observado no gobierna ninguna cuota: es contabilidad, no control de
admisión. El umbral solo destaca el mensaje.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lib_telegram import env_value, load_env, send_telegram  # noqa: E402

HEADER_PREFIX = "[RESIDENCIAFISCAL]"
RPC_TIMEOUT_SECONDS = 30
STRATEGY_LABELS = {
    "current_structured": "A · corpus v3",
    "gemini_file_search": "B · file search",
}
STATUS_LABELS = {
    "completed": "completadas",
    "failed": "fallidas",
    "timed_out": "expiradas",
    "processing": "en curso",
}


def fetch_stats(day: dt.date, env: dict[str, str]) -> dict:
    """Invoca la RPC de agregados con la clave de servicio."""
    url = env_value(env, "SUPABASE_URL").rstrip("/")
    key = env_value(env, "SUPABASE_SECRET_KEY")
    if not url.startswith("https://"):
        raise RuntimeError("Falta SUPABASE_URL en .env")
    if not key:
        raise RuntimeError("Falta SUPABASE_SECRET_KEY en .env")

    request = urllib.request.Request(
        f"{url}/rest/v1/rpc/chat_daily_stats",
        data=json.dumps({"p_day": day.isoformat()}).encode(),
        headers={
            "Content-Type": "application/json",
            "apikey": key,
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=RPC_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:  # pragma: no cover - red
        raise RuntimeError(f"Supabase devolvió {error.code} al pedir chat_daily_stats") from None


def format_usd(microusd: int) -> str:
    return f"${microusd / 1_000_000:,.6f}".replace(",", "@").replace(".", ",").replace("@", ".")


def format_seconds(milliseconds: object) -> str:
    if not isinstance(milliseconds, (int, float)):
        return "—"
    return f"{milliseconds / 1000:.1f} s".replace(".", ",")


def build_message(stats: dict, alert_usd: float | None) -> str:
    day = stats.get("day", "?")
    requests = int(stats.get("requests", 0))
    total_microusd = int(stats.get("total_microusd", 0))
    by_status = stats.get("by_status") or {}
    by_failure = stats.get("by_failure_code") or {}
    by_strategy = stats.get("by_strategy") or {}
    by_measurement = stats.get("by_measurement") or {}

    exceeded = alert_usd is not None and total_microusd / 1_000_000 > alert_usd
    icon = "⚠️" if exceeded or by_failure else "💬"
    lines = [f"{HEADER_PREFIX} {icon} Chat · {day}", ""]

    if requests == 0:
        lines.append("Sin consultas registradas.")
        return "\n".join(lines)

    status_detail = ", ".join(
        f"{count} {STATUS_LABELS.get(status, status)}"
        for status, count in sorted(by_status.items())
    )
    lines.append(f"Consultas: {requests} ({status_detail})")
    lines.append(
        f"Coste: {format_usd(total_microusd)} · "
        f"{stats.get('cost_complete_requests', 0)} con coste ACTUAL completo"
    )
    if exceeded and alert_usd is not None:
        lines.append(f"⚠️ Supera el umbral diario de ${alert_usd:.2f}")
    if by_failure:
        detail = ", ".join(f"{code} {count}" for code, count in sorted(by_failure.items()))
        lines.append(f"Fallos: {detail}")

    if by_strategy:
        lines.append("")
        lines.append("Por estrategia")
        for strategy, detail in sorted(by_strategy.items()):
            label = STRATEGY_LABELS.get(strategy, strategy)
            lines.append(
                f"· {label} — {detail.get('answers', 0)} resp · "
                f"{format_usd(int(detail.get('cost_microusd') or 0))} · "
                f"p50 {format_seconds(detail.get('p50_latency_ms'))} · "
                f"p95 {format_seconds(detail.get('p95_latency_ms'))}"
            )

    if by_measurement:
        detail = " · ".join(f"{name} {count}" for name, count in sorted(by_measurement.items()))
        lines.append("")
        lines.append(f"Medición: {detail}")

    return "\n".join(lines)


def parse_alert_threshold(env: dict[str, str]) -> float | None:
    raw = env_value(env, "CHAT_DAILY_COST_ALERT_USD")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", help="Día en formato YYYY-MM-DD. Por defecto, ayer.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime el mensaje sin enviarlo a Telegram.",
    )
    arguments = parser.parse_args(argv)

    env = load_env()
    day = (
        dt.date.fromisoformat(arguments.day)
        if arguments.day
        else dt.date.today() - dt.timedelta(days=1)
    )
    stats = fetch_stats(day, env)
    message = build_message(stats, parse_alert_threshold(env))

    if arguments.dry_run:
        print(message)
        return 0
    send_telegram(message, env)
    print(f"Resumen del {day.isoformat()} enviado a Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
