"""Contrato del resumen diario del ledger del chat.

El script vive en `scripts/` y se ejecuta con `uv run`, así que se carga por
ruta en lugar de importarse como paquete, igual que el informe semanal.
"""

from __future__ import annotations

import importlib.util
import pathlib
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "daily_chat_cost_telegram.py"
MIGRATION_PATH = ROOT / "supabase" / "migrations" / "20260801210500_chat_daily_stats.sql"


def load_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("daily_chat_cost_telegram", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()

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
        mensaje = MODULE.build_message(STATS, None)

        self.assertIn("[RESIDENCIAFISCAL]", mensaje)
        self.assertIn("2026-08-01", mensaje)
        self.assertIn("12 (11 completadas, 1 fallidas)", mensaje)
        self.assertIn("$0,048231", mensaje)
        self.assertIn("10 con coste ACTUAL completo", mensaje)
        self.assertIn("A · corpus v3", mensaje)
        self.assertIn("B · file search", mensaje)
        self.assertIn("p50 18,2 s", mensaje)
        self.assertIn("p95 19,4 s", mensaje)
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
