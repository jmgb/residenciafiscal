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
import html
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lib_telegram import env_value, load_env, send_telegram  # noqa: E402

HEADER_PREFIX = "[RESIDENCIAFISCAL]"
RPC_TIMEOUT_SECONDS = 30
SERVICE_NAME = "residenciafiscal-daily-chat-cost-telegram.service"
PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = PROJECT_DIR / "reports" / "daily_chat_cost_telegram" / "last_day.txt"
# `Persistent=true` dispara la unit una sola vez al arrancar: sin recuperación,
# una máquina apagada tres días manda un resumen y pierde dos sin dejar rastro.
MAX_CATCH_UP_DAYS = 7
FAILURE_DETAIL_LIMIT = 500
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
    amount = (Decimal(microusd) / Decimal(1_000_000)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return f"${amount:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def format_seconds(milliseconds: object) -> str:
    if not isinstance(milliseconds, (int, float)):
        return "—"
    return f"{milliseconds / 1000:.1f} s".replace(".", ",")


def label(labels: dict[str, str], key: object) -> str:
    """Etiqueta legible de un valor del ledger, listo para `parse_mode=HTML`.

    Un código sin etiqueta sale tal cual del ledger, así que se escapa: el
    mensaje viaja como HTML y un `<` suelto haría que Telegram rechazara el
    envío entero. Los rótulos propios no llevan nada que escapar.
    """
    text = str(key)
    return labels.get(text, html.escape(text))


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
    lines = [f"<b>{HEADER_PREFIX} {icon} Chat · {day}</b>", ""]

    if requests == 0:
        lines.append("Sin consultas registradas.")
        return "\n".join(lines)

    status_detail = ", ".join(
        f"{count} {label(STATUS_LABELS, status)}" for status, count in sorted(by_status.items())
    )
    lines.append(f"Consultas: {requests} ({status_detail})")
    lines.append(
        f"Coste: {format_usd(total_microusd)} · "
        f"{stats.get('cost_complete_requests', 0)} con coste ACTUAL completo"
    )
    if exceeded and alert_usd is not None:
        lines.append(f"⚠️ Supera el umbral diario de ${alert_usd:.2f}")
    if by_failure:
        detail = ", ".join(
            f"{html.escape(str(code))} {count}" for code, count in sorted(by_failure.items())
        )
        lines.append(f"Fallos: {detail}")

    if by_strategy:
        lines.append("")
        lines.append("<b>Por estrategia</b>")
        for strategy, detail in sorted(by_strategy.items()):
            lines.append(
                f"· {label(STRATEGY_LABELS, strategy)} — {detail.get('answers', 0)} resp · "
                f"{format_usd(int(detail.get('cost_microusd') or 0))} · "
                f"Respuesta en: {format_seconds(detail.get('p50_latency_ms'))}"
            )

    if by_measurement:
        detail = " · ".join(
            f"{html.escape(str(name))} {count}" for name, count in sorted(by_measurement.items())
        )
        lines.append("")
        lines.append(f"<b>Medición:</b> {detail}")

    return "\n".join(lines)


def pending_days(
    last_sent: dt.date | None,
    today: dt.date,
    max_days: int = MAX_CATCH_UP_DAYS,
) -> tuple[list[dt.date], list[dt.date]]:
    """Días que faltan por resumir y días demasiado viejos para recuperarlos.

    Sin estado previo solo se manda ayer: el primer arranque no reconstruye la
    historia entera.

    Un `last_sent` posterior a ayer es imposible —lo deja un reloj adelantado
    durante una ejecución— y se trata como estado inválido, no como «nada
    pendiente»: si no, el resumen quedaría mudo hasta que el tiempo real
    alcanzara esa fecha. Se repara mandando ayer, sin inventar los días
    intermedios.
    """
    yesterday = today - dt.timedelta(days=1)
    if last_sent is None or last_sent > yesterday:
        return [yesterday], []
    if last_sent == yesterday:
        return [], []

    days: list[dt.date] = []
    day = last_sent + dt.timedelta(days=1)
    while day <= yesterday:
        days.append(day)
        day += dt.timedelta(days=1)

    if len(days) > max_days:
        return days[-max_days:], days[:-max_days]
    return days, []


def read_last_sent(path: pathlib.Path) -> dt.date | None:
    """Último día resumido. Un estado ausente o corrupto nunca impide el envío."""
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        return None


def write_last_sent(path: pathlib.Path, day: dt.date) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{day.isoformat()}\n", encoding="utf-8")


def build_skipped_message(days: list[dt.date]) -> str:
    """Los días que no se recuperan se declaran; el silencio no es una opción."""
    return "\n".join(
        [
            f"<b>{HEADER_PREFIX} ⚠️ Chat · {len(days)} resúmenes diarios omitidos</b>",
            "",
            f"Sin enviar del {days[0].isoformat()} al {days[-1].isoformat()}.",
            "El ledger de Supabase conserva el dato: recupéralo con <code>--day</code>.",
        ]
    )


def is_manual_invocation(environ: dict[str, str] | None = None) -> bool:
    """¿Viene el aviso de un disparo a mano en vez de del timer?

    systemd exporta `INVOCATION_ID` al servicio y los hijos lo heredan, así que
    su ausencia identifica una ejecución desde la terminal.
    """
    values = environ if environ is not None else dict(os.environ)
    return not values.get("INVOCATION_ID")


def build_failure_message(
    day: dt.date,
    exit_code: int,
    detail: str = "",
    manual: bool = False,
) -> str:
    """Aviso de que el resumen no salió.

    Un disparo manual se marca en la primera línea: `--failure-alert` acepta
    cualquier `--failure-exit-code` desde la terminal, y un mensaje de prueba
    indistinguible de uno real gasta la credibilidad de la alerta. La
    notificación push solo enseña el principio, así que el marcador va delante.
    """
    prefix = f"{HEADER_PREFIX} 🧪 PRUEBA ·" if manual else f"{HEADER_PREFIX} ⚠️"
    lines = [
        f"<b>{prefix} Chat · el resumen diario FALLÓ {day.isoformat()}</b>",
        "",
        f"Exit: {exit_code}",
        "",
        "<b>Revisa:</b>",
        f"<code>journalctl --user -u {SERVICE_NAME} -n 100 --no-pager</code>",
    ]
    if manual:
        lines.insert(1, "")
        lines.insert(2, "Disparo manual fuera de systemd: no ha fallado ningún job.")
    if detail:
        # El detalle es stderr ajeno: sin escapar, un `<` bastaría para que
        # Telegram rechazara el aviso justo el día que hace falta.
        lines.extend(["", f"<pre>{html.escape(detail[:FAILURE_DETAIL_LIMIT])}</pre>"])
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
    parser.add_argument(
        "--catch-up",
        action="store_true",
        help="Recupera los días pendientes desde el último resumen enviado.",
    )
    parser.add_argument("--today", help="Fecha base YYYY-MM-DD para --catch-up. Default: hoy.")
    parser.add_argument(
        "--state-file", help=f"Estado del último día enviado. Default: {DEFAULT_STATE_PATH}."
    )
    parser.add_argument("--failure-alert", help="Envía un aviso de fallo por Telegram y termina.")
    parser.add_argument("--failure-exit-code", type=int, default=1)
    arguments = parser.parse_args(argv)

    env = load_env()
    today = dt.date.fromisoformat(arguments.today) if arguments.today else dt.date.today()

    if arguments.failure_alert:
        message = build_failure_message(
            today,
            arguments.failure_exit_code,
            arguments.failure_alert,
            manual=is_manual_invocation(),
        )
        if arguments.dry_run:
            print(message)
            return 0
        send_telegram(message, env)
        print("Aviso de fallo enviado a Telegram.")
        return 0

    alert_usd = parse_alert_threshold(env)

    if not arguments.catch_up:
        day = (
            dt.date.fromisoformat(arguments.day) if arguments.day else today - dt.timedelta(days=1)
        )
        message = build_message(fetch_stats(day, env), alert_usd)
        if arguments.dry_run:
            print(message)
            return 0
        send_telegram(message, env)
        print(f"Resumen del {day.isoformat()} enviado a Telegram.")
        return 0

    state_path = pathlib.Path(arguments.state_file) if arguments.state_file else DEFAULT_STATE_PATH
    days, skipped = pending_days(read_last_sent(state_path), today)

    if skipped:
        skipped_message = build_skipped_message(skipped)
        if arguments.dry_run:
            print(skipped_message)
        else:
            send_telegram(skipped_message, env)

    if not days:
        print("Sin resúmenes pendientes.")
        return 0

    for day in days:
        message = build_message(fetch_stats(day, env), alert_usd)
        if arguments.dry_run:
            print(message)
            continue
        send_telegram(message, env)
        write_last_sent(state_path, day)
        print(f"Resumen del {day.isoformat()} enviado a Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
