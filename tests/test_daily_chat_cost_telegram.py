"""Contrato del resumen diario del ledger del chat.

El script vive en `scripts/` y se ejecuta con `uv run`, así que se carga por
ruta en lugar de importarse como paquete, igual que el informe semanal.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "supabase" / "migrations" / "20260801210500_chat_daily_stats.sql"


def load_script(name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_script("daily_chat_cost_telegram")

STATS = {
    "day": "2026-08-01",
    "requests": 12,
    "by_status": {"completed": 11, "failed": 1},
    "by_failure_code": {"comparison_error": 1},
    "total_microusd": 48231,
    "cost_complete_requests": 10,
    "by_measurement": {"ACTUAL": 11, "ESTIMATED": 11},
    "by_strategy": {
        "current_structured": {
            "answers": 11,
            "cost_microusd": 27000,
            "p50_latency_ms": 18200,
            "p95_latency_ms": 24100,
        },
        "gemini_file_search": {
            "answers": 11,
            "cost_microusd": 21231,
            "p50_latency_ms": 12000,
            "p95_latency_ms": 19400,
        },
    },
}


class ResumenDiarioTest(unittest.TestCase):
    def test_resume_consultas_coste_y_estrategias(self) -> None:
        mensaje = MODULE.build_message({**STATS, "by_failure_code": {}}, None)

        self.assertEqual(
            mensaje.splitlines()[0],
            "<b>[RESIDENCIAFISCAL] 💬 Chat · 2026-08-01</b>",
        )
        self.assertIn("2026-08-01", mensaje)
        self.assertIn("12 (11 completadas, 1 fallidas)", mensaje)
        self.assertIn("Coste: $0,05 ·", mensaje)
        self.assertIn("10 con coste ACTUAL completo", mensaje)
        self.assertIn("A · corpus v3", mensaje)
        self.assertIn("B · file search", mensaje)
        self.assertIn("Respuesta en: 18,2 s", mensaje)
        self.assertNotIn("p95", mensaje)
        self.assertIn("ACTUAL 11 · ESTIMATED 11", mensaje)

    def test_un_dia_sin_consultas_no_finge_actividad(self) -> None:
        mensaje = MODULE.build_message(
            {"day": "2026-08-02", "requests": 0, "total_microusd": 0}, None
        )

        self.assertIn("Sin consultas registradas.", mensaje)
        self.assertNotIn("Por estrategia", mensaje)

    def test_los_fallos_marcan_el_mensaje(self) -> None:
        self.assertIn("⚠️", MODULE.build_message(STATS, None))
        self.assertIn("comparison_error 1", MODULE.build_message(STATS, None))

    def test_el_umbral_solo_destaca_cuando_se_supera(self) -> None:
        sin_fallos = {**STATS, "by_failure_code": {}}

        bajo = MODULE.build_message(sin_fallos, 1.0)
        self.assertNotIn("Supera el umbral", bajo)
        self.assertIn("💬", bajo)

        alto = MODULE.build_message({**sin_fallos, "total_microusd": 3_000_000}, 1.0)
        self.assertIn("Supera el umbral diario de $1.00", alto)
        self.assertIn("⚠️", alto)

    def test_umbral_invalido_o_ausente_no_alerta(self) -> None:
        self.assertIsNone(MODULE.parse_alert_threshold({}))
        self.assertIsNone(MODULE.parse_alert_threshold({"CHAT_DAILY_COST_ALERT_USD": "abc"}))
        self.assertIsNone(MODULE.parse_alert_threshold({"CHAT_DAILY_COST_ALERT_USD": "0"}))
        self.assertEqual(MODULE.parse_alert_threshold({"CHAT_DAILY_COST_ALERT_USD": "2.5"}), 2.5)

    def test_latencia_ausente_no_se_inventa(self) -> None:
        self.assertEqual(MODULE.format_seconds(None), "—")


class RecuperacionDeDiasTest(unittest.TestCase):
    """Un resumen diario perdido no puede desaparecer en silencio.

    `Persistent=true` dispara la unit una sola vez al arrancar, así que una
    máquina apagada tres días enviaría un mensaje y dejaría dos días sin
    resumen y sin rastro de que faltan.
    """

    def test_sin_estado_previo_solo_manda_ayer(self) -> None:
        pendientes, omitidos = MODULE.pending_days(None, dt.date(2026, 8, 3))

        self.assertEqual(pendientes, [dt.date(2026, 8, 2)])
        self.assertEqual(omitidos, [])

    def test_no_repite_un_dia_ya_enviado(self) -> None:
        pendientes, omitidos = MODULE.pending_days(dt.date(2026, 8, 2), dt.date(2026, 8, 3))

        self.assertEqual(pendientes, [])
        self.assertEqual(omitidos, [])

    def test_recupera_los_dias_perdidos_tras_un_apagon(self) -> None:
        pendientes, omitidos = MODULE.pending_days(dt.date(2026, 7, 30), dt.date(2026, 8, 3))

        self.assertEqual(
            pendientes,
            [dt.date(2026, 7, 31), dt.date(2026, 8, 1), dt.date(2026, 8, 2)],
        )
        self.assertEqual(omitidos, [])

    def test_un_apagon_largo_recorta_y_declara_los_omitidos(self) -> None:
        pendientes, omitidos = MODULE.pending_days(
            dt.date(2026, 7, 30), dt.date(2026, 8, 3), max_days=2
        )

        self.assertEqual(pendientes, [dt.date(2026, 8, 1), dt.date(2026, 8, 2)])
        self.assertEqual(omitidos, [dt.date(2026, 7, 31)])

    def test_un_estado_del_futuro_se_repara_en_vez_de_callar(self) -> None:
        """Un reloj adelantado durante una ejecución deja un `last_sent` imposible.

        Tratarlo como «nada pendiente» dejaría el resumen mudo hasta que el
        tiempo real alcanzara esa fecha, que es justo el silencio que la
        recuperación existe para evitar. Se trata como estado inválido: se
        manda ayer, sin inventar los días intermedios.
        """
        pendientes, omitidos = MODULE.pending_days(dt.date(2026, 8, 20), dt.date(2026, 8, 3))

        self.assertEqual(pendientes, [dt.date(2026, 8, 2)])
        self.assertEqual(omitidos, [])

    def test_los_dias_omitidos_se_declaran_en_telegram(self) -> None:
        mensaje = MODULE.build_skipped_message([dt.date(2026, 7, 28), dt.date(2026, 7, 31)])

        self.assertIn("[RESIDENCIAFISCAL]", mensaje)
        self.assertIn("⚠️", mensaje)
        self.assertIn("2", mensaje)
        self.assertIn("2026-07-28", mensaje)
        self.assertIn("2026-07-31", mensaje)


class EstadoDelUltimoEnvioTest(unittest.TestCase):
    def test_escribe_y_relee_el_ultimo_dia_enviado(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = pathlib.Path(carpeta) / "sub" / "last_day.txt"

            MODULE.write_last_sent(ruta, dt.date(2026, 8, 2))

            self.assertEqual(MODULE.read_last_sent(ruta), dt.date(2026, 8, 2))

    def test_sin_estado_previo_devuelve_none(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            self.assertIsNone(MODULE.read_last_sent(pathlib.Path(carpeta) / "no-existe.txt"))

    def test_un_estado_corrupto_no_rompe_el_envio(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = pathlib.Path(carpeta) / "last_day.txt"
            ruta.write_text("no soy una fecha", encoding="utf-8")

            self.assertIsNone(MODULE.read_last_sent(ruta))


class AvisoDeFalloTest(unittest.TestCase):
    """Un fallo del timer no puede ser indistinguible del silencio."""

    def test_el_aviso_nombra_la_unit_el_exit_y_el_detalle(self) -> None:
        mensaje = MODULE.build_failure_message(
            dt.date(2026, 8, 3), 2, "Supabase devolvió 500 al pedir chat_daily_stats"
        )

        self.assertIn("[RESIDENCIAFISCAL]", mensaje)
        self.assertIn("2026-08-03", mensaje)
        self.assertIn("Exit: 2", mensaje)
        self.assertIn("residenciafiscal-daily-chat-cost-telegram.service", mensaje)
        self.assertIn("Supabase devolvió 500", mensaje)

    def test_el_aviso_no_arrastra_diagnosticos_enormes(self) -> None:
        mensaje = MODULE.build_failure_message(dt.date(2026, 8, 3), 1, "x" * 2000)

        self.assertLess(len(mensaje), 800)


class AvisoDePruebaTest(unittest.TestCase):
    """Una alerta de prueba no puede parecer un fallo real.

    `--failure-alert` se puede disparar a mano con cualquier `--failure-exit-code`,
    y el mensaje resultante era indistinguible del que manda un job roto. Solo lo
    salvaba que alguien escribiera «PRUEBA» a mano en el texto.
    """

    def test_un_disparo_manual_se_marca_en_la_primera_linea(self) -> None:
        """La notificación push solo enseña el principio del mensaje."""
        mensaje = MODULE.build_failure_message(dt.date(2026, 8, 3), 99, "", manual=True)

        self.assertIn("PRUEBA", mensaje.splitlines()[0])

    def test_el_disparo_manual_declara_que_no_ha_fallado_nada(self) -> None:
        mensaje = MODULE.build_failure_message(dt.date(2026, 8, 3), 99, "", manual=True)

        self.assertIn("no ha fallado ningún job", mensaje)

    def test_un_fallo_real_no_se_marca_como_prueba(self) -> None:
        mensaje = MODULE.build_failure_message(dt.date(2026, 8, 3), 2, "Supabase devolvió 500")

        self.assertNotIn("PRUEBA", mensaje)

    def test_systemd_identifica_la_ejecucion_real_por_invocation_id(self) -> None:
        """systemd exporta `INVOCATION_ID` al servicio y los hijos lo heredan."""
        self.assertFalse(MODULE.is_manual_invocation({"INVOCATION_ID": "8f3c"}))

    def test_sin_invocation_id_la_ejecucion_es_manual(self) -> None:
        self.assertTrue(MODULE.is_manual_invocation({}))
        self.assertTrue(MODULE.is_manual_invocation({"INVOCATION_ID": ""}))


class CableadoDelRunnerTest(unittest.TestCase):
    """El runner del timer llama a `main`; la recuperación tiene que llegar ahí."""

    def setUp(self) -> None:
        self.enviados: list[str] = []
        self.dias_pedidos: list[dt.date] = []

        def fetch_stats(day: dt.date, env: dict[str, str]) -> dict:
            self.dias_pedidos.append(day)
            return {"day": day.isoformat(), "requests": 0, "total_microusd": 0}

        dobles = {
            "fetch_stats": fetch_stats,
            "send_telegram": lambda mensaje, env: self.enviados.append(mensaje),
            "load_env": dict,
        }
        for nombre, doble in dobles.items():
            parche = mock.patch.object(MODULE, nombre, doble)
            parche.start()
            self.addCleanup(parche.stop)

    def test_catch_up_envia_los_dias_perdidos_y_avanza_el_estado(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            estado = pathlib.Path(carpeta) / "last_day.txt"
            MODULE.write_last_sent(estado, dt.date(2026, 7, 31))

            codigo = MODULE.main(
                ["--catch-up", "--today", "2026-08-03", "--state-file", str(estado)]
            )

            self.assertEqual(codigo, 0)
            self.assertEqual(self.dias_pedidos, [dt.date(2026, 8, 1), dt.date(2026, 8, 2)])
            self.assertEqual(len(self.enviados), 2)
            self.assertEqual(MODULE.read_last_sent(estado), dt.date(2026, 8, 2))

    def test_catch_up_sin_pendientes_no_manda_nada(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            estado = pathlib.Path(carpeta) / "last_day.txt"
            MODULE.write_last_sent(estado, dt.date(2026, 8, 2))

            codigo = MODULE.main(
                ["--catch-up", "--today", "2026-08-03", "--state-file", str(estado)]
            )

            self.assertEqual(codigo, 0)
            self.assertEqual(self.enviados, [])

    def test_en_seco_no_escribe_el_estado(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            estado = pathlib.Path(carpeta) / "last_day.txt"

            MODULE.main(
                ["--catch-up", "--dry-run", "--today", "2026-08-03", "--state-file", str(estado)]
            )

            self.assertEqual(self.enviados, [])
            self.assertFalse(estado.exists())

    def test_un_apagon_largo_avisa_de_los_dias_que_no_recupera(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            estado = pathlib.Path(carpeta) / "last_day.txt"
            MODULE.write_last_sent(estado, dt.date(2026, 6, 1))

            MODULE.main(["--catch-up", "--today", "2026-08-03", "--state-file", str(estado)])

            self.assertIn("resúmenes diarios omitidos", self.enviados[0])
            self.assertEqual(len(self.dias_pedidos), MODULE.MAX_CATCH_UP_DAYS)

    def test_un_estado_del_futuro_se_reescribe_al_dia_real(self) -> None:
        with tempfile.TemporaryDirectory() as carpeta:
            estado = pathlib.Path(carpeta) / "last_day.txt"
            MODULE.write_last_sent(estado, dt.date(2026, 8, 20))

            MODULE.main(["--catch-up", "--today", "2026-08-03", "--state-file", str(estado)])

            self.assertEqual(self.dias_pedidos, [dt.date(2026, 8, 2)])
            self.assertEqual(MODULE.read_last_sent(estado), dt.date(2026, 8, 2))

    def test_el_aviso_de_fallo_se_manda_y_no_consulta_el_ledger(self) -> None:
        codigo = MODULE.main(
            ["--failure-alert", "Supabase devolvió 500", "--failure-exit-code", "2"]
        )

        self.assertEqual(codigo, 0)
        self.assertEqual(self.dias_pedidos, [])
        self.assertIn("Exit: 2", self.enviados[0])
        self.assertIn("Supabase devolvió 500", self.enviados[0])

    def test_el_aviso_lanzado_desde_systemd_no_se_marca_como_prueba(self) -> None:
        with mock.patch.dict("os.environ", {"INVOCATION_ID": "8f3c"}, clear=False):
            MODULE.main(["--failure-alert", "Supabase devolvió 500", "--failure-exit-code", "2"])

        self.assertNotIn("PRUEBA", self.enviados[0])

    def test_el_aviso_lanzado_a_mano_se_marca_como_prueba(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            MODULE.main(["--failure-alert", "probando la alerta", "--failure-exit-code", "99"])

        self.assertIn("PRUEBA", self.enviados[0])

    def test_el_aviso_en_seco_no_llega_a_telegram(self) -> None:
        """Probar la alerta no debería costar un mensaje falso en el canal real."""
        codigo = MODULE.main(["--failure-alert", "probando", "--dry-run"])

        self.assertEqual(codigo, 0)
        self.assertEqual(self.enviados, [])


class RunnerDelTimerTest(unittest.TestCase):
    """El runner es lo que ejecuta la unit: la recuperación y el aviso viven ahí."""

    RUNNER = (ROOT / "scripts" / "agentic" / "daily_chat_cost_telegram_runner.sh").read_text(
        encoding="utf-8"
    )
    SERVICE = (
        ROOT / "scripts" / "agentic" / "residenciafiscal-daily-chat-cost-telegram.service"
    ).read_text(encoding="utf-8")

    def test_el_runner_recupera_los_dias_pendientes(self) -> None:
        self.assertIn("--catch-up", self.RUNNER)

    def test_el_runner_avisa_por_telegram_cuando_el_envio_falla(self) -> None:
        self.assertIn("--failure-alert", self.RUNNER)
        self.assertIn("--failure-exit-code", self.RUNNER)

    def test_el_aviso_usa_el_interprete_del_sistema(self) -> None:
        """Un entorno de `uv` roto no puede silenciar la alerta."""
        aviso = self.RUNNER.split("--failure-alert")[0]
        self.assertIn("python3 scripts/daily_chat_cost_telegram.py", aviso.rsplit("\n", 2)[-2])

    def test_la_unit_ejecuta_ese_runner(self) -> None:
        self.assertIn("daily_chat_cost_telegram_runner.sh", self.SERVICE)

    def test_la_unit_aguanta_la_recuperacion_mas_larga(self) -> None:
        """Si systemd mata el job a mitad, ni avanza el estado ni sale la alerta.

        El peor caso son `MAX_CATCH_UP_DAYS` días, cada uno con su timeout de
        RPC y su timeout de Telegram, más el aviso de días omitidos.
        """
        lib_telegram = load_script("lib_telegram")
        por_dia = MODULE.RPC_TIMEOUT_SECONDS + lib_telegram.TELEGRAM_TIMEOUT_SECONDS
        peor_caso = (MODULE.MAX_CATCH_UP_DAYS + 1) * por_dia

        declarado = next(
            int(linea.split("=", 1)[1])
            for linea in self.SERVICE.splitlines()
            if linea.startswith("TimeoutStartSec=")
        )

        self.assertGreaterEqual(declarado, peor_caso)


class InstaladorDelTimerTest(unittest.TestCase):
    """El timer semanal tiene instalador idempotente; el diario también."""

    INSTALLER = ROOT / "scripts" / "agentic" / "install-daily-chat-cost-telegram-timer.sh"

    def test_el_instalador_existe(self) -> None:
        self.assertTrue(self.INSTALLER.exists())

    def test_valida_las_claves_que_el_resumen_necesita(self) -> None:
        contenido = self.INSTALLER.read_text(encoding="utf-8")

        for clave in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"):
            self.assertIn(clave, contenido)

    def test_instala_las_dos_units_y_activa_el_timer(self) -> None:
        contenido = self.INSTALLER.read_text(encoding="utf-8")

        self.assertIn("residenciafiscal-daily-chat-cost-telegram.service", contenido)
        self.assertIn("residenciafiscal-daily-chat-cost-telegram.timer", contenido)
        self.assertIn("daemon-reload", contenido)
        self.assertIn("enable --now", contenido)


class PrivacidadDeLaRpcTest(unittest.TestCase):
    """La RPC es la única puerta del script al ledger: no puede leer contenido."""

    def test_la_rpc_no_toca_columnas_de_contenido(self) -> None:
        sql = MIGRATION_PATH.read_text(encoding="utf-8")

        for columna in ("m.content", "content,", "content)", "question", "answer_text"):
            self.assertNotIn(columna, sql, f"la RPC no debe leer {columna}")

    def test_la_rpc_queda_reservada_al_rol_de_servicio(self) -> None:
        sql = MIGRATION_PATH.read_text(encoding="utf-8")

        self.assertIn("SECURITY DEFINER", sql)
        self.assertIn("SET search_path = pg_catalog", sql)
        self.assertIn(
            "REVOKE ALL ON FUNCTION public.chat_daily_stats(date) FROM PUBLIC, anon, authenticated;",
            sql,
        )
        self.assertIn(
            "GRANT EXECUTE ON FUNCTION public.chat_daily_stats(date) TO service_role;",
            sql,
        )


if __name__ == "__main__":
    unittest.main()
