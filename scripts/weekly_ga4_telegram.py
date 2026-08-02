#!/usr/bin/env python3
"""Envía por Telegram el resumen semanal de tráfico de residenciafiscal.org.

Mide visitas, usuarios únicos y retención (qué parte de los usuarios de la
semana ya había visitado antes) en **las dos analíticas del sitio**, GA4 y
PostHog, y las presenta por separado.

No se promedian ni se elige una como «la buena» a propósito: cuentan cosas
distintas y divergen mucho. GA4 registra bots que ejecutan JavaScript y PostHog
apenas los ve; el desglose y el porqué están en
`docs/operations/WEEKLY_TRAFFIC_REPORT.md`. Presentarlas juntas es lo que hace
visible esa diferencia en vez de esconderla detrás de una cifra única.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import pathlib
import sys
import tempfile
import urllib.request
from typing import IO, Any, NamedTuple

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]
ENV_PATHS = [PROJECT_DIR / ".env"]
TELEGRAM_HEADER_PREFIX = "[RESIDENCIAFISCAL]"
SUCCESS_ICON = "✅"
REPORT_TITLE = "Análisis Tráfico"
PROJECT_SITE_LABEL = "RESIDENCIAFISCAL"
SERVICE_NAME = "residenciafiscal-weekly-ga4-telegram.service"
DEFAULT_HISTORY_DIR = PROJECT_DIR / "reports" / "weekly_ga4_telegram"
POSTHOG_TRAFFIC_HOST = "residenciafiscal.org"
POSTHOG_QUERY_TIMEOUT_SECONDS = 90
TELEGRAM_TIMEOUT_SECONDS = 30


class DateWindow(NamedTuple):
    start: dt.date
    end: dt.date


class PeriodTraffic(NamedTuple):
    pageviews: int
    users: int
    returning_users: int
    #: Solo GA4: usuarios que no caen ni en «new» ni en «returning».
    unclassified_users: int = 0
    #: Solo GA4: sesiones y cuántas de ellas tuvieron interacción real. Es lo
    #: que separa a una persona de un rastreador, que entra una vez y se va.
    sessions: int = 0
    engaged_sessions: int = 0


class PostHogTraffic(NamedTuple):
    host: str
    current: PeriodTraffic
    previous: PeriodTraffic


class SearchPeriod(NamedTuple):
    clicks: int
    impressions: int
    #: Posición media ponderada por impresiones; `None` sin impresiones.
    position: float | None


class SearchConsoleTraffic(NamedTuple):
    site_url: str
    current: SearchPeriod
    previous: SearchPeriod
    #: Ventanas realmente consultadas: van desplazadas respecto a las del
    #: informe por el retraso de publicación de la API (ver compute_gsc_windows).
    window: DateWindow | None = None
    previous_window: DateWindow | None = None


class SiteMetric(NamedTuple):
    code: str
    property_key: str
    property_id: str
    current: PeriodTraffic
    previous: PeriodTraffic


EMPTY_PERIOD = PeriodTraffic(pageviews=0, users=0, returning_users=0)


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------


def load_env(paths: list[pathlib.Path] = ENV_PATHS) -> dict[str, str]:
    """Lee pares `CLAVE=valor` sin ejecutar el fichero: nunca se hace `source`."""
    values: dict[str, str] = {}
    for path in paths:
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


def discover_properties(env: dict[str, str]) -> list[tuple[str, str, str]]:
    """Propiedades GA4 declaradas. Sin ninguna, el informe se queda en PostHog."""
    properties: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    default_property_id = env.get("GA4_PROPERTY_ID", "")
    if default_property_id:
        properties.append((PROJECT_SITE_LABEL, "GA4_PROPERTY_ID", default_property_id))
        seen.add(default_property_id)
    for key in sorted(env):
        if not key.startswith("GA4_PROPERTY_ID_"):
            continue
        property_id = env.get(key, "")
        if not property_id or property_id in seen:
            continue
        properties.append((key.removeprefix("GA4_PROPERTY_ID_"), key, property_id))
        seen.add(property_id)
    return properties


# ---------------------------------------------------------------------------
# Ventanas y formato
# ---------------------------------------------------------------------------


def compute_windows(today: dt.date) -> tuple[DateWindow, DateWindow]:
    """Últimos siete días cerrados y los siete inmediatamente anteriores."""
    current_end = today - dt.timedelta(days=1)
    current_start = current_end - dt.timedelta(days=6)
    previous_end = current_start - dt.timedelta(days=1)
    previous_start = previous_end - dt.timedelta(days=6)
    return DateWindow(current_start, current_end), DateWindow(previous_start, previous_end)


def format_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def format_variation(current: int, previous: int) -> str:
    if previous == 0:
        return "nuevo" if current > 0 else "0,0%"
    variation = ((current - previous) / previous) * 100
    sign = "+" if variation > 0 else ""
    return f"{sign}{variation:.1f}%".replace(".", ",")


def format_share(value: int, total: int) -> str:
    if total == 0:
        return "0,0%"
    return f"{(value / total) * 100:.1f}%".replace(".", ",")


def format_plural(value: int, singular: str, plural: str) -> str:
    return f"{format_int(value)} {singular if value == 1 else plural}"


def compute_change_pct(current: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def compute_share_pct(value: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((value / total) * 100, 1)


# ---------------------------------------------------------------------------
# PostHog
# ---------------------------------------------------------------------------


def build_posthog_query(host: str, current: DateWindow, previous: DateWindow) -> str:
    """HogQL con usuarios, visitas y recurrentes de las dos ventanas.

    Recurrente es quien ya tenía una visita anterior al inicio de su propia
    ventana, así que la cifra de la semana pasada se calcula con el mismo
    criterio y las dos son comparables.
    """
    safe_host = host.replace("\\", "\\\\").replace("'", "\\'")
    current_start = f"{current.start} 00:00:00"
    previous_start = f"{previous.start} 00:00:00"
    exclusive_end = f"{current.end + dt.timedelta(days=1)} 00:00:00"
    return (
        "WITH primeras AS ("
        " SELECT person_id AS pid, min(timestamp) AS first_seen"
        " FROM events"
        " WHERE event = '$pageview'"
        f" AND properties.$host = '{safe_host}'"
        " GROUP BY person_id"
        ")"
        " SELECT v.period AS period,"
        " count(distinct v.person_id) AS usuarios,"
        " count(distinct if(p.first_seen < v.period_start, v.person_id, NULL)) AS recurrentes,"
        " count() AS visitas"
        " FROM ("
        " SELECT"
        f" if(timestamp >= toDateTime('{current_start}'), 'current', 'previous') AS period,"
        f" if(timestamp >= toDateTime('{current_start}'),"
        f" toDateTime('{current_start}'), toDateTime('{previous_start}')) AS period_start,"
        " person_id AS person_id"
        " FROM events"
        " WHERE event = '$pageview'"
        f" AND properties.$host = '{safe_host}'"
        f" AND timestamp >= toDateTime('{previous_start}')"
        f" AND timestamp < toDateTime('{exclusive_end}')"
        ") AS v"
        " LEFT JOIN primeras AS p ON p.pid = v.person_id"
        " GROUP BY period"
    )


def parse_posthog_rows(rows: list[Any], host: str) -> PostHogTraffic:
    periods = {
        str(row[0]): PeriodTraffic(
            pageviews=int(row[3]), users=int(row[1]), returning_users=int(row[2])
        )
        for row in rows
        if len(row) >= 4
    }
    return PostHogTraffic(
        host=host,
        current=periods.get("current", EMPTY_PERIOD),
        previous=periods.get("previous", EMPTY_PERIOD),
    )


def fetch_posthog_traffic(
    env: dict[str, str], current: DateWindow, previous: DateWindow
) -> PostHogTraffic:
    query_host = env_value(env, "POSTHOG_QUERY_HOST")
    project_id = env_value(env, "POSTHOG_PROJECT_ID")
    api_key = env_value(env, "POSTHOG_PERSONAL_API_KEY", "POSTHOG_API_KEY")
    if not query_host or not project_id or not api_key:
        raise RuntimeError(
            "Falta POSTHOG_QUERY_HOST, POSTHOG_PROJECT_ID o POSTHOG_PERSONAL_API_KEY en .env"
        )

    traffic_host = env_value(env, "POSTHOG_TRAFFIC_HOST") or POSTHOG_TRAFFIC_HOST
    query = build_posthog_query(traffic_host, current, previous)
    payload = json.dumps({"query": {"kind": "HogQLQuery", "query": query}}).encode()
    request = urllib.request.Request(
        f"{query_host.rstrip('/')}/api/projects/{project_id}/query/",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=POSTHOG_QUERY_TIMEOUT_SECONDS) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("error"):
        raise RuntimeError(f"PostHog devolvió error: {result['error']}")
    return parse_posthog_rows(result.get("results", []), traffic_host)


# ---------------------------------------------------------------------------
# GA4
# ---------------------------------------------------------------------------


#: Orden en que se piden y se leen las métricas sin dimensión de GA4.
GA4_TOTAL_METRICS = ("activeUsers", "screenPageViews", "sessions", "engagedSessions")


def build_ga4_period(
    totals: tuple[str, str, str, str] | None, buckets: list[tuple[str, str]]
) -> PeriodTraffic:
    """Compone el periodo a partir de los dos informes que hacen falta.

    `activeUsers` **no es aditivo** entre dimensiones: la suma de los cubos
    `new` / `returning` / sin etiqueta no tiene por qué dar el total. Por eso el
    total se lee de un informe sin dimensión y el desglose solo aporta los
    recurrentes y el resto sin clasificar.
    """
    if totals is None:
        return EMPTY_PERIOD
    users, pageviews, sessions, engaged_sessions = (int(value) for value in totals)
    counts = {label: int(value) for label, value in buckets}
    return PeriodTraffic(
        pageviews=pageviews,
        users=users,
        sessions=sessions,
        engaged_sessions=engaged_sessions,
        returning_users=counts.get("returning", 0),
        unclassified_users=sum(v for k, v in counts.items() if k not in {"new", "returning"}),
    )


def configure_google_credentials(env: dict[str, str]) -> IO[str] | None:
    credentials_json = env_value(env, "GA4_CREDENTIALS_JSON")
    if credentials_json:
        tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
        tmp.write(credentials_json)
        tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
        return tmp

    credentials = env_value(env, "GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials:
        raise RuntimeError("Falta GOOGLE_APPLICATION_CREDENTIALS o GA4_CREDENTIALS_JSON")
    credentials_path = pathlib.Path(credentials)
    if not credentials_path.is_absolute():
        credentials_path = PROJECT_DIR / credentials_path
    if not credentials_path.exists():
        raise RuntimeError(f"No existe GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
    return None


def fetch_ga4_period(property_id: str, window: DateWindow) -> PeriodTraffic:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    client = BetaAnalyticsDataClient()
    date_range = DateRange(start_date=window.start.isoformat(), end_date=window.end.isoformat())

    totals_response = client.run_report(
        RunReportRequest(
            property=f"properties/{property_id}",
            metrics=[Metric(name=name) for name in GA4_TOTAL_METRICS],
            date_ranges=[date_range],
            limit=1,
        )
    )
    if not totals_response.rows:
        return EMPTY_PERIOD
    values = totals_response.rows[0].metric_values
    totals = (values[0].value, values[1].value, values[2].value, values[3].value)

    buckets_response = client.run_report(
        RunReportRequest(
            property=f"properties/{property_id}",
            metrics=[Metric(name="activeUsers")],
            dimensions=[Dimension(name="newVsReturning")],
            date_ranges=[date_range],
            limit=10,
        )
    )
    buckets = [
        (row.dimension_values[0].value, row.metric_values[0].value) for row in buckets_response.rows
    ]
    return build_ga4_period(totals, buckets)


def collect_ga4_metrics(
    env: dict[str, str], current: DateWindow, previous: DateWindow
) -> list[SiteMetric]:
    properties = discover_properties(env)
    if not properties:
        return []
    tmp_credentials = configure_google_credentials(env)
    try:
        return [
            SiteMetric(
                code=code,
                property_key=property_key,
                property_id=property_id,
                current=fetch_ga4_period(property_id, current),
                previous=fetch_ga4_period(property_id, previous),
            )
            for code, property_key, property_id in properties
        ]
    finally:
        if tmp_credentials:
            pathlib.Path(tmp_credentials.name).unlink(missing_ok=True)


def aggregate_ga4(rows: list[SiteMetric]) -> tuple[PeriodTraffic, PeriodTraffic]:
    def total(periods: list[PeriodTraffic]) -> PeriodTraffic:
        return PeriodTraffic(
            pageviews=sum(p.pageviews for p in periods),
            users=sum(p.users for p in periods),
            returning_users=sum(p.returning_users for p in periods),
            unclassified_users=sum(p.unclassified_users for p in periods),
            sessions=sum(p.sessions for p in periods),
            engaged_sessions=sum(p.engaged_sessions for p in periods),
        )

    return total([row.current for row in rows]), total([row.previous for row in rows])


# ---------------------------------------------------------------------------
# Search Console
# ---------------------------------------------------------------------------
#
# Es la métrica del gate SEO —clicks, impresiones y posición—, no otra medida
# de visitas. Ojo al desfase: la API publica los datos con ~2 días de retraso,
# así que los últimos días de la ventana pueden llegar incompletos; la
# comparación semana contra semana sigue siendo homogénea porque las dos
# ventanas sufren el mismo recorte.


EMPTY_SEARCH_PERIOD = SearchPeriod(clicks=0, impressions=0, position=None)

#: La API de Search Console publica con ~2 días de retraso. Con 3 de margen,
#: las dos ventanas consultadas están siempre completas.
GSC_LAG_DAYS = 3


def compute_gsc_windows(today: dt.date) -> tuple[DateWindow, DateWindow]:
    """Dos semanas completas terminadas al menos `GSC_LAG_DAYS` antes de hoy.

    Consultar las mismas ventanas que GA4/PostHog compararía ~5 días de la
    semana en curso (recortada por el retraso) contra 7 de la anterior, y la
    variación saldría siempre en caída. Se desplazan las dos.
    """
    end = today - dt.timedelta(days=GSC_LAG_DAYS)
    current = DateWindow(end - dt.timedelta(days=6), end)
    previous_end = current.start - dt.timedelta(days=1)
    return current, DateWindow(previous_end - dt.timedelta(days=6), previous_end)


def parse_gsc_totals(
    site_url: str, current_response: dict[str, Any], previous_response: dict[str, Any]
) -> SearchConsoleTraffic:
    def period(response: dict[str, Any]) -> SearchPeriod:
        rows = response.get("rows") or []
        if not rows:
            return EMPTY_SEARCH_PERIOD
        row = rows[0]
        return SearchPeriod(
            clicks=int(row.get("clicks", 0)),
            impressions=int(row.get("impressions", 0)),
            position=row.get("position"),
        )

    return SearchConsoleTraffic(
        site_url=site_url, current=period(current_response), previous=period(previous_response)
    )


def fetch_gsc_traffic(
    env: dict[str, str], current: DateWindow, previous: DateWindow
) -> SearchConsoleTraffic | None:
    """Totales de búsqueda de las dos ventanas; `None` si no hay propiedad."""
    site_url = env_value(env, "GSC_SITE_URL")
    if not site_url:
        return None

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)

    def query(window: DateWindow) -> dict[str, Any]:
        return (
            service.searchanalytics()
            .query(
                siteUrl=site_url,
                body={"startDate": window.start.isoformat(), "endDate": window.end.isoformat()},
            )
            .execute()
        )

    traffic = parse_gsc_totals(site_url, query(current), query(previous))
    return traffic._replace(window=current, previous_window=previous)


def collect_search_console(
    env: dict[str, str], current: DateWindow, previous: DateWindow
) -> tuple[SearchConsoleTraffic | None, str | None]:
    """Nunca tumba el informe: un fallo de GSC se declara como línea propia.

    Sin `GSC_SITE_URL` la fuente está apagada a propósito: ni se configuran
    credenciales —una instalación solo-PostHog no las tiene— ni se declara
    error alguno.
    """
    if not env_value(env, "GSC_SITE_URL"):
        return None, None
    tmp_credentials = None
    try:
        tmp_credentials = configure_google_credentials(env)
        return fetch_gsc_traffic(env, current, previous), None
    except Exception as error:  # noqa: BLE001 — el informe debe salir igual.
        return None, f"{type(error).__name__}: {error}"[:120]
    finally:
        if tmp_credentials:
            pathlib.Path(tmp_credentials.name).unlink(missing_ok=True)


def format_position(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def build_gsc_line(traffic: SearchConsoleTraffic) -> str:
    current, previous = traffic.current, traffic.previous
    if current.impressions == 0 and previous.impressions == 0:
        return "Search Console: sin impresiones en buscadores todavía."
    linea = (
        f"Search Console: {format_int(current.clicks)} clicks "
        f"({format_variation(current.clicks, previous.clicks)}), "
        f"{format_plural(current.impressions, 'impresión', 'impresiones')} "
        f"({format_variation(current.impressions, previous.impressions)}), "
        f"CTR {format_share(current.clicks, current.impressions)}"
    )
    if current.position is not None:
        linea += f", posición media {format_position(current.position)}"
    return linea + "."


# ---------------------------------------------------------------------------
# Mensaje e histórico
# ---------------------------------------------------------------------------


def build_source_line(label: str, current: PeriodTraffic, previous: PeriodTraffic) -> str:
    linea = (
        f"{label}: {format_plural(current.pageviews, 'visita', 'visitas')} "
        f"({format_variation(current.pageviews, previous.pageviews)}), "
        f"{format_plural(current.users, 'usuario', 'usuarios')} "
        f"({format_variation(current.users, previous.users)}), "
        f"{format_plural(current.returning_users, 'recurrente', 'recurrentes')} "
        f"({format_share(current.returning_users, current.users)})."
    )
    # Solo GA4 aporta sesiones. Es la cláusula que distingue a una persona de un
    # rastreador: los bots entran una vez, no interactúan y se van.
    if current.sessions:
        linea += (
            f" {format_int(current.engaged_sessions)} de "
            f"{format_plural(current.sessions, 'sesión', 'sesiones')} con interacción "
            f"({format_share(current.engaged_sessions, current.sessions)})."
        )
    return linea


def join_sources(sources: list[str]) -> str:
    """«A y B» con dos fuentes, «A, B y C» con tres: la conjunción solo una vez."""
    if len(sources) == 1:
        return sources[0]
    return f"{', '.join(sources[:-1])} y {sources[-1]}"


def build_message(
    ga4_rows: list[SiteMetric],
    posthog: PostHogTraffic,
    run_date: dt.date | None = None,
    search_console: SearchConsoleTraffic | None = None,
    search_console_error: str | None = None,
) -> str:
    lines = [f"{SUCCESS_ICON} {REPORT_TITLE} {(run_date or dt.date.today()).isoformat()}", ""]
    sources = []
    if ga4_rows:
        current, previous = aggregate_ga4(ga4_rows)
        lines.append(build_source_line("GA4", current, previous))
        sources.append(f"GA4 ({', '.join(f'propiedad {row.property_id}' for row in ga4_rows)})")
    lines.append(build_source_line("PostHog", posthog.current, posthog.previous))
    sources.append(f"PostHog ({posthog.host})")
    if search_console is not None:
        lines.append(build_gsc_line(search_console))
        sources.append(f"Search Console ({search_console.site_url})")
    elif search_console_error is not None:
        # El fallo se declara en su línea, nunca en silencio; pero una fuente
        # que no aportó datos no se lista como fuente.
        lines.append(f"Search Console: no disponible esta semana ({search_console_error}).")
    lines.extend(["", f"Fuente: {join_sources(sources)}."])
    return "\n".join(lines)


def window_to_dict(window: DateWindow) -> dict[str, str]:
    return {"start": window.start.isoformat(), "end": window.end.isoformat()}


def period_to_dict(current: PeriodTraffic, previous: PeriodTraffic) -> dict[str, Any]:
    return {
        "pageviews": current.pageviews,
        "previous_pageviews": previous.pageviews,
        "pageviews_change_pct": compute_change_pct(current.pageviews, previous.pageviews),
        "users": current.users,
        "previous_users": previous.users,
        "users_change_pct": compute_change_pct(current.users, previous.users),
        "returning_users": current.returning_users,
        "previous_returning_users": previous.returning_users,
        "returning_share_pct": compute_share_pct(current.returning_users, current.users),
        "previous_returning_share_pct": compute_share_pct(previous.returning_users, previous.users),
        "unclassified_users": current.unclassified_users,
        "sessions": current.sessions,
        "engaged_sessions": current.engaged_sessions,
        "engaged_share_pct": compute_share_pct(current.engaged_sessions, current.sessions),
        "previous_engaged_share_pct": compute_share_pct(
            previous.engaged_sessions, previous.sessions
        ),
    }


def search_console_to_dict(traffic: SearchConsoleTraffic | None) -> dict[str, Any] | None:
    if traffic is None:
        return None
    current, previous = traffic.current, traffic.previous
    return {
        "site_url": traffic.site_url,
        "window": window_to_dict(traffic.window) if traffic.window else None,
        "previous_window": (
            window_to_dict(traffic.previous_window) if traffic.previous_window else None
        ),
        "clicks": current.clicks,
        "previous_clicks": previous.clicks,
        "clicks_change_pct": compute_change_pct(current.clicks, previous.clicks),
        "impressions": current.impressions,
        "previous_impressions": previous.impressions,
        "impressions_change_pct": compute_change_pct(current.impressions, previous.impressions),
        "ctr_pct": compute_share_pct(current.clicks, current.impressions),
        "position": current.position,
        "previous_position": previous.position,
    }


def build_history_record(
    ga4_rows: list[SiteMetric],
    posthog: PostHogTraffic,
    current_window: DateWindow,
    previous_window: DateWindow,
    run_date: dt.date,
    search_console: SearchConsoleTraffic | None = None,
) -> dict[str, Any]:
    ga4: dict[str, Any] | None = None
    if ga4_rows:
        current, previous = aggregate_ga4(ga4_rows)
        ga4 = {
            "metric": "activeUsers",
            "sites": {
                row.code: {
                    "property_key": row.property_key,
                    "property_id": row.property_id,
                    **period_to_dict(row.current, row.previous),
                }
                for row in ga4_rows
            },
            "global": period_to_dict(current, previous),
        }
    return {
        "report_type": "weekly_ga4_telegram",
        "generated_for": run_date.isoformat(),
        "window": window_to_dict(current_window),
        "previous_window": window_to_dict(previous_window),
        "posthog": {"host": posthog.host, **period_to_dict(posthog.current, posthog.previous)},
        "ga4": ga4,
        "search_console": search_console_to_dict(search_console),
    }


def write_history(
    record: dict[str, Any],
    output_dir: pathlib.Path = DEFAULT_HISTORY_DIR,
) -> dict[str, pathlib.Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dated_path = output_dir / f"{record['generated_for']}.json"
    latest_path = output_dir / "latest.json"
    payload = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    dated_path.write_text(payload)
    latest_path.write_text(payload)
    return {"dated": dated_path, "latest": latest_path}


def build_failure_message(run_date: dt.date, exit_code: int, detail: str = "") -> str:
    lines = [
        f"Tráfico semanal FALLÓ {run_date.isoformat()}",
        "",
        f"Exit: {exit_code}.",
        f"Revisa: journalctl --user -u {SERVICE_NAME} -n 100 --no-pager",
    ]
    if detail:
        lines.extend(["", detail[:500]])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def build_telegram_payload(chat_id: str, message: str) -> dict[str, Any]:
    first_line, sep, rest = message.partition("\n")
    header = html.escape(f"{TELEGRAM_HEADER_PREFIX} {first_line}", quote=False)
    body = html.escape(rest, quote=False)
    return {
        "chat_id": chat_id,
        "text": f"<b>{header}</b>" + sep + body,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


def send_telegram(message: str, env: dict[str, str]) -> None:
    token = env_value(env, "TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN", "TELEGRAM_TOKEN")
    chat_id = env_value(env, "TELEGRAM_CHAT_ID", "TG_CHAT_ID")
    thread_id = env_value(env, "TELEGRAM_MESSAGE_THREAD_ID", "TG_THREAD_ID")
    if not token:
        raise RuntimeError("Falta TELEGRAM_TOKEN en .env")
    if not chat_id:
        raise RuntimeError("Falta TELEGRAM_CHAT_ID en .env")

    payload = build_telegram_payload(chat_id, message)
    if thread_id:
        payload["message_thread_id"] = thread_id
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TELEGRAM_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Telegram devolvió error: {body}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Fecha base YYYY-MM-DD. Default: hoy.")
    parser.add_argument("--dry-run", action="store_true", help="Imprime el mensaje sin enviarlo.")
    parser.add_argument(
        "--no-history", action="store_true", help="No escribe reports/weekly_ga4_telegram."
    )
    parser.add_argument("--failure-alert", help="Envía un aviso de fallo por Telegram y termina.")
    parser.add_argument("--failure-exit-code", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    env = load_env()
    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    if args.failure_alert:
        send_telegram(build_failure_message(today, args.failure_exit_code, args.failure_alert), env)
        print("Alerta de fallo enviada por Telegram.")
        return 0

    current, previous = compute_windows(today)
    posthog = fetch_posthog_traffic(env, current, previous)
    ga4_rows = collect_ga4_metrics(env, current, previous)
    gsc, gsc_error = collect_search_console(env, *compute_gsc_windows(today))
    message = build_message(
        ga4_rows, posthog, today, search_console=gsc, search_console_error=gsc_error
    )
    if args.dry_run:
        print(message)
        return 0

    if not args.no_history:
        paths = write_history(
            build_history_record(ga4_rows, posthog, current, previous, today, search_console=gsc)
        )
        print(f"Histórico escrito: {paths['dated']}")
    send_telegram(message, env)
    print("Mensaje enviado por Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
