"""Guardián de frescura del resumen diario del ledger del chat.

El resumen diario solo avisa cuando **corre y falla**: si el timer no llega a
dispararse —máquina apagada, timer parado, unit desinstalada tras un `git pull`
sin reinstalar—, no hay mensaje de error y el silencio es indistinguible del
éxito. Este check cierra ese hueco, igual que `check-backup-freshness.sh` lo
cierra para los backups del VPS.

**Su límite es real y no se disimula**: comparte máquina con lo que vigila, así
que no puede avisar de un apagón mientras dura. Lo que sí detecta, y en el acto:

- el estado congelado (el digest lleva días sin avanzar `last_day.txt`),
- el timer parado o desinstalado, aunque el estado aún parezca fresco,
- el digest que nunca llegó a enviar nada.

Tras un apagón largo, `Persistent=true` lo dispara al arrancar y el aviso sale
entonces. Vigilarlo desde fuera de la máquina exige mover el timer al VPS, que
es una decisión aparte y no de este script.

No reimplementa la lectura del estado: importa la del propio digest, porque un
guardián que parsea el fichero por su cuenta acaba divergiendo de quien lo
escribe, y entonces miente en la dirección peor —diciendo que todo está bien—.

Solo usa la librería estándar y **no toca el ledger**: lee un fichero local y el
estado de una unit. No sabe nada del contenido del chat.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from daily_chat_cost_telegram import (  # noqa: E402
    DEFAULT_STATE_PATH,
    HEADER_PREFIX,
    is_manual_invocation,
    read_last_sent,
)
from lib_telegram import env_value, load_env, send_telegram  # noqa: E402

SERVICE_NAME = "residenciafiscal-daily-chat-cost-freshness.service"
WATCHED_TIMER = "residenciafiscal-daily-chat-cost-telegram.timer"
WATCHED_SERVICE = "residenciafiscal-daily-chat-cost-telegram.service"
# El digest corre a las 09:15 y deja el estado en «ayer». A las 10:15 un desfase
# de un día ya es real: no es un retraso, es que no corrió.
DEFAULT_MAX_STALENESS_DAYS = 1
SYSTEMCTL_TIMEOUT_SECONDS = 15
CRASH_DETAIL_LIMIT = 500
# Los mismos alias que acepta `send_telegram`: comprobar solo el nombre canónico
# declararía roto un canal que funciona.
TELEGRAM_TOKEN_KEYS = ("TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN", "TELEGRAM_TOKEN")
TELEGRAM_CHAT_KEYS = ("TELEGRAM_CHAT_ID", "TG_CHAT_ID")
EXIT_CRASHED = 1
EXIT_CHANNEL_UNAVAILABLE = 3


def staleness_days(last_sent: dt.date | None, today: dt.date) -> int | None:
    """Días de retraso respecto al último resumen que debería existir.

    `0` es estar al día. Un valor negativo delata un estado imposible —lo deja un
    reloj adelantado durante una ejecución—: el digest lo repara solo, pero aquí
    no puede pasar por fresco.
    """
    if last_sent is None:
        return None
    return (today - dt.timedelta(days=1) - last_sent).days


def run_systemctl(argv: list[str]) -> tuple[int, str]:
    completed = subprocess.run(  # noqa: S603
        ["systemctl", "--user", *argv],
        capture_output=True,
        text=True,
        timeout=SYSTEMCTL_TIMEOUT_SECONDS,
    )
    return completed.returncode, completed.stdout.strip()


def timer_state(run: object = None) -> str | None:
    """Estado del timer vigilado, o `None` si no se puede saber.

    En CI y en un contenedor no hay bus de usuario. Que falte systemd no puede
    tumbar al guardián: el resto de comprobaciones siguen siendo válidas.
    """
    caller = run if run is not None else run_systemctl
    try:
        _, output = caller(["is-active", WATCHED_TIMER])  # type: ignore[operator]
    except (OSError, subprocess.SubprocessError):
        return None
    return output or None


def build_stale_message(last_sent: dt.date, staleness: int) -> str:
    return "\n".join(
        [
            f"{HEADER_PREFIX} ⚠️ Chat · el resumen diario lleva {staleness} día(s) sin salir",
            "",
            f"Último día resumido: {last_sent.isoformat()}.",
            "El digest no avisa de esto por su cuenta: si el timer no dispara, calla.",
            f"Revisa: systemctl --user list-timers {WATCHED_TIMER}",
            f"        journalctl --user -u {WATCHED_SERVICE} -n 50 --no-pager",
        ]
    )


def build_never_sent_message() -> str:
    return "\n".join(
        [
            f"{HEADER_PREFIX} ⚠️ Chat · el resumen diario no se ha enviado nunca",
            "",
            "No hay estado de ningún envío previo.",
            "Si el timer se acaba de instalar, esto se apaga solo tras el primer resumen.",
            f"Revisa: systemctl --user list-timers {WATCHED_TIMER}",
        ]
    )


def missing_telegram_keys(env: dict[str, str]) -> list[str]:
    """Claves que impedirían avisar, comprobadas **en cada pasada**.

    Con todo al día el check sale por el camino del silencio, así que sin esta
    comprobación el canal solo se ejercía el día que había algo que avisar: justo
    el peor momento para descubrir que el token desapareció del `.env`.
    """
    missing: list[str] = []
    if not env_value(env, *TELEGRAM_TOKEN_KEYS):
        missing.append("TELEGRAM_TOKEN")
    if not env_value(env, *TELEGRAM_CHAT_KEYS):
        missing.append("TELEGRAM_CHAT_ID")
    return missing


def mark_as_test(message: str) -> str:
    """Marca un aviso disparado a mano, con la misma regla que el resumen diario.

    El guardián es un emisor de alertas más: si probarlo mete en el canal un
    mensaje indistinguible de uno real, se gasta la credibilidad de todos.
    """
    head, _, rest = message.partition("\n")
    head = head.replace(f"{HEADER_PREFIX} ⚠️", f"{HEADER_PREFIX} 🧪 PRUEBA ·", 1)
    return "\n".join(
        [head, "", "Disparo manual fuera de systemd: no ha fallado ningún job.", rest.lstrip("\n")]
    )


def build_crash_message(error: BaseException) -> str:
    """El guardián no puede ser más frágil que lo que vigila.

    Si revienta y solo lo registra el journal, reaparece el silencio que existe
    para eliminar. El detalle se corta como en el aviso del digest.
    """
    return "\n".join(
        [
            f"{HEADER_PREFIX} ⚠️ Chat · el guardián del resumen diario FALLÓ",
            "",
            f"{type(error).__name__}: {str(error)[:CRASH_DETAIL_LIMIT]}",
            "",
            "No se ha comprobado si el resumen diario sigue saliendo.",
            f"Revisa: journalctl --user -u {SERVICE_NAME} -n 50 --no-pager",
        ]
    )


def build_timer_stopped_message(state: str) -> str:
    return "\n".join(
        [
            f"{HEADER_PREFIX} ⚠️ Chat · el timer del resumen diario no está activo",
            "",
            f"Estado de {WATCHED_TIMER}: {state}.",
            "Un `git pull` que toque las units no las reinstala solo.",
            "Repara: bash scripts/agentic/install-daily-chat-cost-telegram-timer.sh",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", help="Fecha base YYYY-MM-DD. Default: hoy.")
    parser.add_argument("--state-file", help=f"Estado del digest. Default: {DEFAULT_STATE_PATH}.")
    parser.add_argument("--dry-run", action="store_true", help="Imprime sin enviar a Telegram.")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Imprime el veredicto aunque todo esté al día (verificación manual).",
    )
    parser.add_argument(
        "--max-staleness-days",
        type=int,
        default=DEFAULT_MAX_STALENESS_DAYS,
        help=f"Días de retraso tolerados. Default: {DEFAULT_MAX_STALENESS_DAYS}.",
    )
    arguments = parser.parse_args(argv)

    # En seco no hay envío que proteger, y exigir credenciales impediría probar
    # el check sin `.env`. La unit real nunca usa `--dry-run`.
    env = load_env()
    if not arguments.dry_run:
        missing = missing_telegram_keys(env)
        if missing:
            print(
                f"No hay canal para avisar: falta {', '.join(missing)} en .env. "
                "El guardián no puede avisar por Telegram de que no puede avisar "
                "por Telegram, así que falla ruidosamente.",
                file=sys.stderr,
            )
            return EXIT_CHANNEL_UNAVAILABLE

    try:
        return run(arguments, env)
    except Exception as error:  # noqa: BLE001 - el guardián no puede morir callado
        if arguments.dry_run:
            print(build_crash_message(error))
            return EXIT_CRASHED
        try:
            send_telegram(build_crash_message(error), env)
        except Exception:  # noqa: BLE001 - aquí termina la cadena
            print(f"el guardián falló y tampoco pudo avisar: {error}", file=sys.stderr)
        else:
            print(f"el guardián falló y avisó por Telegram: {error}", file=sys.stderr)
        return EXIT_CRASHED


def run(arguments: argparse.Namespace, env: dict[str, str]) -> int:
    today = dt.date.fromisoformat(arguments.today) if arguments.today else dt.date.today()
    state_path = pathlib.Path(arguments.state_file) if arguments.state_file else DEFAULT_STATE_PATH
    last_sent = read_last_sent(state_path)
    staleness = staleness_days(last_sent, today)

    alerts: list[str] = []
    if last_sent is None:
        alerts.append(build_never_sent_message())
    elif staleness is not None and staleness >= arguments.max_staleness_days:
        alerts.append(build_stale_message(last_sent, staleness))
    elif staleness is not None and staleness < 0:
        alerts.append(build_stale_message(last_sent, staleness))

    state = timer_state()
    if state is not None and state != "active":
        alerts.append(build_timer_stopped_message(state))

    if not alerts:
        message = f"Resumen diario al día (último: {last_sent}, timer: {state or 'desconocido'})."
        if arguments.report:
            print(message)
        return 0

    manual = is_manual_invocation()
    for alert in alerts:
        message = mark_as_test(alert) if manual else alert
        if arguments.dry_run:
            print(message)
            continue
        send_telegram(message, env)
        print("Aviso de frescura enviado a Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
