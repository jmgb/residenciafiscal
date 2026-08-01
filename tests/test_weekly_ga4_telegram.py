"""Contrato del informe semanal de tráfico que se envía por Telegram.

El script vive en `scripts/` y se ejecuta con `uv run`, así que se carga por
ruta en lugar de importarse como paquete.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import pathlib
import tempfile
import types
import unittest

SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "weekly_ga4_telegram.py"


def load_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("weekly_ga4_telegram", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def periodo(
    pageviews: int,
    users: int,
    returning_users: int,
    unclassified_users: int = 0,
    sessions: int = 0,
    engaged_sessions: int = 0,
):
    return MODULE.PeriodTraffic(
        pageviews=pageviews,
        users=users,
        returning_users=returning_users,
        unclassified_users=unclassified_users,
        sessions=sessions,
        engaged_sessions=engaged_sessions,
    )


def posthog(current, previous, host: str = "residenciafiscal.org"):
    return MODULE.PostHogTraffic(host=host, current=current, previous=previous)


def sitio(current, previous, code: str = "RESIDENCIAFISCAL", property_id: str = "547477728"):
    return MODULE.SiteMetric(
        code=code,
        property_key="GA4_PROPERTY_ID",
        property_id=property_id,
        current=current,
        previous=previous,
    )


class VentanasTests(unittest.TestCase):
    def test_la_ventana_cubre_los_siete_dias_cerrados_anteriores(self):
        current, previous = MODULE.compute_windows(dt.date(2026, 8, 3))

        self.assertEqual(current.start, dt.date(2026, 7, 27))
        self.assertEqual(current.end, dt.date(2026, 8, 2))
        self.assertEqual(previous.start, dt.date(2026, 7, 20))
        self.assertEqual(previous.end, dt.date(2026, 7, 26))

    def test_las_dos_ventanas_no_se_solapan_y_son_consecutivas(self):
        current, previous = MODULE.compute_windows(dt.date(2026, 1, 1))

        self.assertEqual(previous.end + dt.timedelta(days=1), current.start)


class FormatoTests(unittest.TestCase):
    def test_la_variacion_cubre_subida_bajada_y_base_cero(self):
        self.assertEqual(MODULE.format_variation(120, 100), "+20,0%")
        self.assertEqual(MODULE.format_variation(75, 100), "-25,0%")
        self.assertEqual(MODULE.format_variation(0, 0), "0,0%")
        self.assertEqual(MODULE.format_variation(7, 0), "nuevo")

    def test_el_porcentaje_sobre_total_no_divide_por_cero(self):
        self.assertEqual(MODULE.format_share(0, 0), "0,0%")
        self.assertEqual(MODULE.format_share(1, 4), "25,0%")

    def test_los_enteros_usan_separador_de_miles_espanol(self):
        self.assertEqual(MODULE.format_int(1234567), "1.234.567")


class ConsultaPostHogTests(unittest.TestCase):
    def test_la_consulta_filtra_por_host_y_por_las_dos_ventanas(self):
        current = MODULE.DateWindow(dt.date(2026, 7, 27), dt.date(2026, 8, 2))
        previous = MODULE.DateWindow(dt.date(2026, 7, 20), dt.date(2026, 7, 26))

        query = MODULE.build_posthog_query("residenciafiscal.org", current, previous)

        self.assertIn("'residenciafiscal.org'", query)
        self.assertIn("2026-07-27 00:00:00", query)
        self.assertIn("2026-07-20 00:00:00", query)
        # El límite superior es exclusivo: el día siguiente al final de la ventana.
        self.assertIn("2026-08-03 00:00:00", query)

    def test_el_host_no_puede_inyectar_hogql(self):
        window = MODULE.DateWindow(dt.date(2026, 7, 27), dt.date(2026, 8, 2))

        query = MODULE.build_posthog_query("mal'o", window, window)

        self.assertIn("'mal\\'o'", query)

    def test_las_filas_se_convierten_en_los_dos_periodos(self):
        rows = [["current", 4, 1, 30], ["previous", 5, 3, 42]]

        traffic = MODULE.parse_posthog_rows(rows, "residenciafiscal.org")

        self.assertEqual(traffic.host, "residenciafiscal.org")
        self.assertEqual(traffic.current, periodo(pageviews=30, users=4, returning_users=1))
        self.assertEqual(traffic.previous, periodo(pageviews=42, users=5, returning_users=3))

    def test_un_periodo_sin_trafico_vale_cero_y_no_rompe(self):
        traffic = MODULE.parse_posthog_rows([["current", 1, 0, 7]], "residenciafiscal.org")

        self.assertEqual(traffic.previous, periodo(pageviews=0, users=0, returning_users=0))


class LecturaGa4Tests(unittest.TestCase):
    """GA4 devuelve el desglose new/returning por separado del total.

    `activeUsers` no es aditivo entre dimensiones: la suma de los cubos
    new/returning/(not set) no tiene por qué dar el total, así que el total se
    lee sin dimensión y el desglose solo aporta los recurrentes.
    """

    def test_el_total_sale_del_informe_sin_dimension(self):
        period = MODULE.build_ga4_period(totals=("81", "168", "96", "24"), buckets=[])

        self.assertEqual(period.users, 81)
        self.assertEqual(period.pageviews, 168)

    def test_los_recurrentes_salen_del_cubo_returning(self):
        period = MODULE.build_ga4_period(
            totals=("81", "168", "96", "24"), buckets=[("new", "79"), ("returning", "2")]
        )

        self.assertEqual(period.returning_users, 2)

    def test_el_cubo_sin_etiqueta_se_contabiliza_como_no_clasificado(self):
        period = MODULE.build_ga4_period(
            totals=("81", "168", "96", "24"),
            buckets=[("new", "79"), ("returning", "2"), ("", "17")],
        )

        self.assertEqual(period.unclassified_users, 17)
        self.assertEqual(period.returning_users, 2)

    def test_las_sesiones_con_interaccion_se_leen_del_mismo_informe(self):
        period = MODULE.build_ga4_period(totals=("81", "168", "96", "24"), buckets=[])

        self.assertEqual(period.sessions, 96)
        self.assertEqual(period.engaged_sessions, 24)

    def test_una_ventana_sin_datos_devuelve_ceros(self):
        self.assertEqual(MODULE.build_ga4_period(totals=None, buckets=[]), MODULE.EMPTY_PERIOD)


class MensajeTests(unittest.TestCase):
    def setUp(self):
        self.posthog = posthog(
            current=periodo(pageviews=7, users=1, returning_users=0),
            previous=periodo(pageviews=0, users=0, returning_users=0),
        )
        self.ga4 = [
            sitio(
                current=periodo(
                    pageviews=168,
                    users=81,
                    returning_users=2,
                    unclassified_users=17,
                    sessions=96,
                    engaged_sessions=24,
                ),
                previous=periodo(
                    pageviews=120, users=60, returning_users=6, sessions=70, engaged_sessions=35
                ),
            )
        ]

    def test_cada_analitica_ocupa_su_propia_linea_sin_promediarse(self):
        message = MODULE.build_message(self.ga4, self.posthog, dt.date(2026, 8, 3))

        self.assertEqual(message.splitlines()[0], "✅ Análisis Tráfico 2026-08-03")
        self.assertIn(
            "GA4: 168 visitas (+40,0%), 81 usuarios (+35,0%), 2 recurrentes (2,5%).", message
        )
        self.assertIn(
            "PostHog: 7 visitas (nuevo), 1 usuario (nuevo), 0 recurrentes (0,0%).", message
        )

    def test_solo_ga4_declara_las_sesiones_con_interaccion(self):
        message = MODULE.build_message(self.ga4, self.posthog, dt.date(2026, 8, 3))

        ga4_line = next(line for line in message.splitlines() if line.startswith("GA4:"))
        posthog_line = next(line for line in message.splitlines() if line.startswith("PostHog:"))
        self.assertIn("24 de 96 sesiones con interacción (25,0%).", ga4_line)
        self.assertNotIn("interacción", posthog_line)

    def test_una_sola_sesion_concuerda_en_singular(self):
        rows = [
            sitio(
                current=periodo(
                    pageviews=2, users=1, returning_users=0, sessions=1, engaged_sessions=1
                ),
                previous=MODULE.EMPTY_PERIOD,
            )
        ]

        message = MODULE.build_message(rows, self.posthog, dt.date(2026, 8, 3))

        self.assertIn("1 de 1 sesión con interacción (100,0%).", message)

    def test_la_fuente_nombra_las_dos_analiticas_para_no_mezclarlas(self):
        message = MODULE.build_message(self.ga4, self.posthog, dt.date(2026, 8, 3))

        self.assertIn(
            "Fuente: GA4 (propiedad 547477728) y PostHog (residenciafiscal.org).", message
        )

    def test_sin_ga4_solo_queda_posthog_y_no_se_menciona_ga4(self):
        message = MODULE.build_message([], self.posthog, dt.date(2026, 8, 3))

        self.assertIn(
            "PostHog: 7 visitas (nuevo), 1 usuario (nuevo), 0 recurrentes (0,0%).", message
        )
        self.assertIn("Fuente: PostHog (residenciafiscal.org).", message)
        self.assertNotIn("GA4", message)

    def test_el_singular_concuerda_en_las_tres_magnitudes(self):
        singular = posthog(
            current=periodo(pageviews=1, users=1, returning_users=1),
            previous=MODULE.EMPTY_PERIOD,
        )

        message = MODULE.build_message([], singular, dt.date(2026, 8, 3))

        self.assertIn(
            "PostHog: 1 visita (nuevo), 1 usuario (nuevo), 1 recurrente (100,0%).", message
        )

    def test_varias_propiedades_ga4_se_agregan_en_una_sola_linea(self):
        rows = [
            sitio(
                current=periodo(pageviews=100, users=50, returning_users=5),
                previous=periodo(pageviews=80, users=40, returning_users=4),
            ),
            sitio(
                current=periodo(pageviews=68, users=31, returning_users=1),
                previous=periodo(pageviews=40, users=20, returning_users=2),
                code="OTRO",
                property_id="999",
            ),
        ]

        message = MODULE.build_message(rows, self.posthog, dt.date(2026, 8, 3))

        self.assertIn("GA4: 168 visitas (+40,0%), 81 usuarios (+35,0%), 6 recurrentes", message)
        self.assertIn("propiedad 547477728, propiedad 999", message)


class HistoricoTests(unittest.TestCase):
    def setUp(self):
        self.posthog = posthog(
            current=periodo(pageviews=7, users=1, returning_users=0),
            previous=periodo(pageviews=0, users=0, returning_users=0),
        )
        self.ga4 = [
            sitio(
                current=periodo(
                    pageviews=168,
                    users=81,
                    returning_users=2,
                    unclassified_users=17,
                    sessions=96,
                    engaged_sessions=24,
                ),
                previous=periodo(
                    pageviews=120, users=60, returning_users=6, sessions=70, engaged_sessions=35
                ),
            )
        ]
        self.current = MODULE.DateWindow(dt.date(2026, 7, 27), dt.date(2026, 8, 2))
        self.previous = MODULE.DateWindow(dt.date(2026, 7, 20), dt.date(2026, 7, 26))

    def registro(self, ga4_rows=None):
        return MODULE.build_history_record(
            self.ga4 if ga4_rows is None else ga4_rows,
            self.posthog,
            self.current,
            self.previous,
            dt.date(2026, 8, 3),
        )

    def test_el_registro_guarda_ventanas_e_identificacion(self):
        record = self.registro()

        self.assertEqual(record["report_type"], "weekly_ga4_telegram")
        self.assertEqual(record["generated_for"], "2026-08-03")
        self.assertEqual(record["window"], {"start": "2026-07-27", "end": "2026-08-02"})
        self.assertEqual(record["previous_window"], {"start": "2026-07-20", "end": "2026-07-26"})

    def test_sin_ga4_el_bloque_queda_explicitamente_nulo(self):
        self.assertIsNone(self.registro(ga4_rows=[])["ga4"])

    def test_el_bloque_posthog_conserva_sus_cifras_junto_a_las_de_ga4(self):
        posthog_record = self.registro()["posthog"]

        self.assertEqual(posthog_record["host"], "residenciafiscal.org")
        self.assertEqual(posthog_record["pageviews"], 7)
        self.assertEqual(posthog_record["users"], 1)
        self.assertEqual(posthog_record["returning_share_pct"], 0.0)

    def test_el_bloque_ga4_desglosa_propiedad_no_clasificados_y_totales(self):
        ga4 = self.registro()["ga4"]

        site = ga4["sites"]["RESIDENCIAFISCAL"]
        self.assertEqual(site["property_id"], "547477728")
        self.assertEqual(site["users"], 81)
        self.assertEqual(site["pageviews"], 168)
        self.assertEqual(site["returning_users"], 2)
        self.assertEqual(site["unclassified_users"], 17)
        self.assertEqual(site["sessions"], 96)
        self.assertEqual(site["engaged_sessions"], 24)
        self.assertEqual(ga4["global"]["users_change_pct"], 35.0)
        self.assertEqual(ga4["global"]["returning_share_pct"], 2.5)
        self.assertEqual(ga4["global"]["engaged_share_pct"], 25.0)
        self.assertEqual(ga4["global"]["previous_engaged_share_pct"], 50.0)

    def test_se_escribe_el_fichero_fechado_y_el_latest_con_el_mismo_contenido(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = pathlib.Path(tmp)

            paths = MODULE.write_history(self.registro(), output_dir)

            self.assertEqual(paths["dated"].name, "2026-08-03.json")
            self.assertEqual(
                json.loads(paths["dated"].read_text()), json.loads(paths["latest"].read_text())
            )


class ConfiguracionTests(unittest.TestCase):
    def test_sin_property_id_no_hay_ga4_y_no_es_un_error(self):
        self.assertEqual(MODULE.discover_properties({}), [])

    def test_el_property_id_por_defecto_se_etiqueta_con_el_proyecto(self):
        properties = MODULE.discover_properties({"GA4_PROPERTY_ID": "123"})

        self.assertEqual(properties, [(MODULE.PROJECT_SITE_LABEL, "GA4_PROPERTY_ID", "123")])

    def test_las_propiedades_extra_se_descubren_por_sufijo_sin_duplicar(self):
        env = {
            "GA4_PROPERTY_ID": "123",
            "GA4_PROPERTY_ID_OTRO": "456",
            "GA4_PROPERTY_ID_DUP": "123",
        }

        codes = [code for code, _, _ in MODULE.discover_properties(env)]

        self.assertEqual(codes, [MODULE.PROJECT_SITE_LABEL, "OTRO"])

    def test_las_variables_de_entorno_ganan_al_env_del_repo(self):
        self.assertEqual(MODULE.env_value({"A": "fichero"}, "A"), "fichero")
        self.assertEqual(MODULE.env_value({}, "NO_EXISTE"), "")

    def test_el_env_se_parsea_sin_ejecutarlo_y_sin_comillas(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / ".env"
            path.write_text('# comentario\nA="uno"\nB=$(rm -rf /)\nSIN_IGUAL\n')

            values = MODULE.load_env([path])

            self.assertEqual(values["A"], "uno")
            self.assertEqual(values["B"], "$(rm -rf /)")
            self.assertNotIn("SIN_IGUAL", values)


class TelegramTests(unittest.TestCase):
    def test_el_mensaje_va_prefijado_con_el_proyecto_y_escapado_como_html(self):
        payload = MODULE.build_telegram_payload("42", "Título <b>\nCuerpo & más")

        self.assertEqual(payload["chat_id"], "42")
        self.assertEqual(payload["parse_mode"], "HTML")
        self.assertTrue(payload["text"].startswith("<b>[RESIDENCIAFISCAL] Título &lt;b&gt;</b>\n"))
        self.assertIn("Cuerpo &amp; más", payload["text"])

    def test_el_aviso_de_fallo_apunta_al_journal_de_la_unidad_correcta(self):
        message = MODULE.build_failure_message(dt.date(2026, 8, 3), 3, "detalle")

        self.assertIn("residenciafiscal-weekly-ga4-telegram.service", message)
        self.assertIn("Exit: 3.", message)
        self.assertIn("detalle", message)


if __name__ == "__main__":
    unittest.main()
