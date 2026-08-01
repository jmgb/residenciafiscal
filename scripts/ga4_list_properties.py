#!/usr/bin/env python3
"""Lista las propiedades GA4 que ve la cuenta de servicio configurada.

Sirve para dos cosas al conectar GA4: comprobar que el permiso de lectura sobre
la propiedad ya está concedido y averiguar su **ID numérico**, que es lo que
pide `GA4_PROPERTY_ID` (el `G-XXXXXXX` del frontend es el measurement ID y no
vale aquí).

    uv run --with google-analytics-admin --with google-auth \\
        python scripts/ga4_list_properties.py

Reutiliza `configure_google_credentials` del informe semanal, así que respeta
`GA4_CREDENTIALS_JSON` y `GOOGLE_APPLICATION_CREDENTIALS` del `.env`.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]
REPORT_SCRIPT = PROJECT_DIR / "scripts" / "weekly_ga4_telegram.py"


def load_report_module():
    spec = importlib.util.spec_from_file_location("weekly_ga4_telegram", REPORT_SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover - ruta imposible en el repo
        raise RuntimeError(f"No se pudo cargar {REPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    report = load_report_module()
    env = report.load_env()
    tmp_credentials = report.configure_google_credentials(env)
    try:
        from google.analytics.admin_v1beta import AnalyticsAdminServiceClient

        client = AnalyticsAdminServiceClient()
        encontrada = False
        for account in client.list_account_summaries():
            print(f"{account.account}  {account.display_name}")
            for prop in account.property_summaries:
                encontrada = True
                numeric_id = prop.property.removeprefix("properties/")
                print(f"    GA4_PROPERTY_ID={numeric_id}  # {prop.display_name}")
        if not encontrada:
            print(
                "La cuenta de servicio no ve ninguna propiedad. Falta darle rol Lector"
                " en GA4 → Administrar → Accesos a la propiedad.",
                file=sys.stderr,
            )
            return 1
    finally:
        if tmp_credentials:
            pathlib.Path(tmp_credentials.name).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
