"""Contrato del guardián de frescura del resumen diario del chat.

El resumen solo avisa cuando **corre y falla**. Si el timer no dispara —WSL2
apagado, timer parado, unit desinstalada— nadie se entera: el silencio es
indistinguible del éxito. Este check cierra ese hueco, igual que
`check-backup-freshness` hace con los backups.

Su límite es explícito y no se disimula: comparte máquina con lo que vigila, así
que no detecta un apagón *mientras* dura. Avisa al volver, y detecta en el acto
el timer parado, el estado congelado y la unit desinstalada.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_script(name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_script("check_daily_chat_cost_freshness")


class DesfaseTest(unittest.TestCase):
    """El digest de las 09:15 deja el estado en «ayer»; a las 10:15 debe estarlo."""

    def test_el_estado_en_ayer_esta_al_dia(self) -> None:
        self.assertEqual(MODULE.staleness_days(dt.date(2026, 8, 2), dt.date(2026, 8, 3)), 0)

    def test_un_dia_sin_resumir_ya_es_desfase(self) -> None:
        self.assertEqual(MODULE.staleness_days(dt.date(2026, 8, 1), dt.date(2026, 8, 3)), 1)

    def test_sin_estado_no_finge_frescura(self) -> None:
        self.assertIsNone(MODULE.staleness_days(None, dt.date(2026, 8, 3)))

    def test_un_estado_del_futuro_no_cuenta_como_fresco(self) -> None:
        """Lo deja un reloj adelantado; el digest lo repara, el check lo declara."""
        self.assertLess(MODULE.staleness_days(dt.date(2026, 8, 20), dt.date(2026, 8, 3)), 0)


class MensajesTest(unittest.TestCase):
    def test_el_aviso_de_desfase_nombra_el_ultimo_dia_y_como_mirarlo(self) -> None:
        mensaje = MODULE.build_stale_message(dt.date(2026, 7, 30), 3)

        self.assertIn("[RESIDENCIAFISCAL]", mensaje)
        self.assertIn("⚠️", mensaje)
        self.assertIn("2026-07-30", mensaje)
        self.assertIn("3", mensaje)
        self.assertIn("residenciafiscal-daily-chat-cost-telegram.timer", mensaje)

    def test_no_haberse_enviado_nunca_se_dice_distinto(self) -> None:
        """«Sin estado» no es lo mismo que «lleva tres días sin mandar»."""
        mensaje = MODULE.build_never_sent_message()

        self.assertIn("[RESIDENCIAFISCAL]", mensaje)
        self.assertIn("nunca", mensaje.lower())

    def test_el_aviso_del_timer_parado_nombra_su_estado(self) -> None:
        mensaje = MODULE.build_timer_stopped_message("inactive")

        self.assertIn("residenciafiscal-daily-chat-cost-telegram.timer", mensaje)
        self.assertIn("inactive", mensaje)


class TimerVigiladoTest(unittest.TestCase):
    """La señal más temprana: el timer parado, antes de acumular desfase."""

    def test_un_timer_activo_no_alerta(self) -> None:
        self.assertEqual(MODULE.timer_state(run=lambda argv: (0, "active")), "active")

    def test_un_timer_parado_devuelve_su_estado(self) -> None:
        self.assertEqual(MODULE.timer_state(run=lambda argv: (3, "inactive")), "inactive")

    def test_sin_systemd_el_check_no_revienta(self) -> None:
        """En CI no hay bus de usuario; eso no puede tumbar el guardián."""

        def sin_systemctl(argv: list[str]) -> tuple[int, str]:
            raise FileNotFoundError("systemctl")

        self.assertIsNone(MODULE.timer_state(run=sin_systemctl))


class CableadoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.enviados: list[str] = []
        dobles = {
            "send_telegram": lambda mensaje, env: self.enviados.append(mensaje),
            "load_env": dict,
            "timer_state": lambda run=None: "active",
        }
        for nombre, doble in dobles.items():
            parche = mock.patch.object(MODULE, nombre, doble)
            parche.start()
            self.addCleanup(parche.stop)

    def estado_con(self, dia: dt.date | None) -> str:
        carpeta = tempfile.mkdtemp()
        ruta = pathlib.Path(carpeta) / "last_day.txt"
        if dia is not None:
            ruta.write_text(f"{dia.isoformat()}\n", encoding="utf-8")
        return str(ruta)

    def test_con_todo_al_dia_no_manda_nada(self) -> None:
        """Un check que habla a diario deja de leerse."""
        codigo = MODULE.main(
            ["--today", "2026-08-03", "--state-file", self.estado_con(dt.date(2026, 8, 2))]
        )

        self.assertEqual(codigo, 0)
        self.assertEqual(self.enviados, [])

    def test_un_estado_congelado_alerta(self) -> None:
        codigo = MODULE.main(
            ["--today", "2026-08-03", "--state-file", self.estado_con(dt.date(2026, 7, 30))]
        )

        self.assertEqual(codigo, 0)
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("2026-07-30", self.enviados[0])

    def test_sin_estado_alerta_de_que_nunca_se_envio(self) -> None:
        MODULE.main(["--today", "2026-08-03", "--state-file", self.estado_con(None)])

        self.assertEqual(len(self.enviados), 1)
        self.assertIn("nunca", self.enviados[0].lower())

    def test_el_timer_parado_alerta_aunque_el_estado_este_fresco(self) -> None:
        with mock.patch.object(MODULE, "timer_state", lambda run=None: "inactive"):
            MODULE.main(
                ["--today", "2026-08-03", "--state-file", self.estado_con(dt.date(2026, 8, 2))]
            )

        self.assertEqual(len(self.enviados), 1)
        self.assertIn("inactive", self.enviados[0])

    def test_en_seco_no_manda_aunque_haya_desfase(self) -> None:
        MODULE.main(
            [
                "--today",
                "2026-08-03",
                "--dry-run",
                "--state-file",
                self.estado_con(dt.date(2026, 7, 30)),
            ]
        )

        self.assertEqual(self.enviados, [])

    def test_la_tolerancia_es_configurable(self) -> None:
        """Un día de margen sirve para no pisarse con un digest lento."""
        MODULE.main(
            [
                "--today",
                "2026-08-03",
                "--max-staleness-days",
                "2",
                "--state-file",
                self.estado_con(dt.date(2026, 8, 1)),
            ]
        )

        self.assertEqual(self.enviados, [])

    def test_lee_el_estado_igual_que_lo_escribe_el_digest(self) -> None:
        """Reimplementar el parseo del estado es cómo divergen guardián y vigilado.

        Se compara contra el módulo que el propio check importó —el de
        `sys.modules`—, no contra una carga nueva por ruta: dos cargas
        independientes del mismo fichero dan funciones distintas y el test
        pasaría a medir el cargador en vez del cableado.
        """
        digest = sys.modules["daily_chat_cost_telegram"]

        self.assertIs(MODULE.read_last_sent, digest.read_last_sent)
        self.assertEqual(MODULE.DEFAULT_STATE_PATH, digest.DEFAULT_STATE_PATH)


class UnitsTest(unittest.TestCase):
    AGENTIC = ROOT / "scripts" / "agentic"

    def test_la_unit_y_su_timer_existen(self) -> None:
        for nombre in (
            "residenciafiscal-daily-chat-cost-freshness.service",
            "residenciafiscal-daily-chat-cost-freshness.timer",
        ):
            self.assertTrue((self.AGENTIC / nombre).exists(), nombre)

    def test_el_check_corre_despues_del_digest(self) -> None:
        """A las 09:15 manda el digest; comprobarlo antes solo daría falsos positivos."""
        digest = (self.AGENTIC / "residenciafiscal-daily-chat-cost-telegram.timer").read_text()
        check = (self.AGENTIC / "residenciafiscal-daily-chat-cost-freshness.timer").read_text()

        def hora(contenido: str) -> str:
            linea = next(x for x in contenido.splitlines() if x.startswith("OnCalendar="))
            return linea.split("*-*-* ", 1)[1].split(" ", 1)[0]

        self.assertGreater(hora(check), hora(digest))

    def test_el_timer_del_check_recupera_el_disparo_perdido(self) -> None:
        """Sin `Persistent=true` el guardián callaría justo tras un apagón largo."""
        contenido = (self.AGENTIC / "residenciafiscal-daily-chat-cost-freshness.timer").read_text()

        self.assertIn("Persistent=true", contenido)

    def test_la_unit_ejecuta_el_check(self) -> None:
        contenido = (
            self.AGENTIC / "residenciafiscal-daily-chat-cost-freshness.service"
        ).read_text()

        self.assertIn("check_daily_chat_cost_freshness.py", contenido)

    def test_el_instalador_tambien_instala_el_guardian(self) -> None:
        contenido = (self.AGENTIC / "install-daily-chat-cost-telegram-timer.sh").read_text()

        self.assertIn("residenciafiscal-daily-chat-cost-freshness.service", contenido)
        self.assertIn("residenciafiscal-daily-chat-cost-freshness.timer", contenido)


if __name__ == "__main__":
    unittest.main()
