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


CREDENCIALES = {"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}


class CableadoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.enviados: list[str] = []
        dobles = {
            "send_telegram": lambda mensaje, env: self.enviados.append(mensaje),
            "load_env": lambda: dict(CREDENCIALES),
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


class CanalDeAvisoTest(unittest.TestCase):
    """El canal solo se usaba el día que hacía falta, que es el peor para probarlo.

    Con todo al día el check salía por el camino del silencio **antes** de tocar
    el `.env`, así que un `TELEGRAM_TOKEN` desaparecido no se descubría hasta la
    primera alerta de verdad: justo cuando ya no puede avisar de nada.
    """

    def test_las_claves_que_faltan_se_nombran(self) -> None:
        """Con `os.environ` aislado: `env_value` lo consulta antes que el `.env`,
        y sin aislarlo el test mediría la máquina en vez del código."""
        with mock.patch.dict("os.environ", {}, clear=True):
            faltan = MODULE.missing_telegram_keys({})

        self.assertEqual(faltan, ["TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"])

    def test_una_clave_exportada_al_entorno_cuenta_como_presente(self) -> None:
        """`send_telegram` la usaría, así que declararla ausente sería mentir."""
        with mock.patch.dict("os.environ", {"TELEGRAM_TOKEN": "t"}, clear=True):
            faltan = MODULE.missing_telegram_keys({"TELEGRAM_CHAT_ID": "c"})

        self.assertEqual(faltan, [])

    def test_un_canal_completo_no_echa_de_menos_nada(self) -> None:
        self.assertEqual(MODULE.missing_telegram_keys(dict(CREDENCIALES)), [])

    def test_acepta_los_mismos_alias_que_el_envio(self) -> None:
        """`send_telegram` admite `TG_BOT_TOKEN` y `TG_CHAT_ID`; comprobar solo el
        nombre canónico declararía roto un canal que funciona."""
        alias = {"TG_BOT_TOKEN": "t", "TG_CHAT_ID": "c"}

        self.assertEqual(MODULE.missing_telegram_keys(alias), [])

    def test_sin_canal_el_check_falla_ruidosamente_aunque_todo_este_al_dia(self) -> None:
        """No puede avisar por Telegram de que no puede avisar por Telegram."""
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch.object(MODULE, "load_env", dict):
                with mock.patch.object(MODULE, "timer_state", lambda run=None: "active"):
                    carpeta = tempfile.mkdtemp()
                    estado = pathlib.Path(carpeta) / "last_day.txt"
                    estado.write_text("2026-08-02\n", encoding="utf-8")

                    codigo = MODULE.main(["--today", "2026-08-03", "--state-file", str(estado)])

        self.assertNotEqual(codigo, 0)


class FalloDelPropioGuardianTest(unittest.TestCase):
    """El guardián no puede ser más frágil que lo que vigila.

    Si revienta, systemd lo marca `failed` y nadie lo lee: es la misma clase de
    silencio que existe para eliminar, un nivel más arriba.
    """

    def setUp(self) -> None:
        self.enviados: list[str] = []
        parche = mock.patch.object(
            MODULE, "send_telegram", lambda mensaje, env: self.enviados.append(mensaje)
        )
        parche.start()
        self.addCleanup(parche.stop)
        parche_env = mock.patch.object(MODULE, "load_env", lambda: dict(CREDENCIALES))
        parche_env.start()
        self.addCleanup(parche_env.stop)

    def revienta(self, *args: object, **kwargs: object) -> None:
        raise OSError("systemctl colgado")

    def test_un_fallo_del_check_avisa_por_telegram(self) -> None:
        with mock.patch.object(MODULE, "timer_state", self.revienta):
            codigo = MODULE.main(["--today", "2026-08-03"])

        self.assertNotEqual(codigo, 0)
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("systemctl colgado", self.enviados[0])

    def test_el_aviso_del_fallo_nombra_su_propia_unit(self) -> None:
        with mock.patch.object(MODULE, "timer_state", self.revienta):
            MODULE.main(["--today", "2026-08-03"])

        self.assertIn("residenciafiscal-daily-chat-cost-freshness.service", self.enviados[0])

    def test_si_ni_el_aviso_sale_el_check_falla_ruidosamente(self) -> None:
        """La cadena termina aquí: queda el journal y un exit distinto de cero."""

        def telegram_roto(mensaje: str, env: dict[str, str]) -> None:
            raise RuntimeError("Telegram devolvió error")

        with mock.patch.object(MODULE, "timer_state", self.revienta):
            with mock.patch.object(MODULE, "send_telegram", telegram_roto):
                codigo = MODULE.main(["--today", "2026-08-03"])

        self.assertNotEqual(codigo, 0)

    def test_en_seco_el_aviso_de_fallo_tampoco_llega_a_telegram(self) -> None:
        """Probar el guardián en seco no puede costar una alerta falsa en el canal."""
        with mock.patch.object(MODULE, "timer_state", self.revienta):
            codigo = MODULE.main(["--today", "2026-08-03", "--dry-run"])

        self.assertNotEqual(codigo, 0)
        self.assertEqual(self.enviados, [])

    def test_el_aviso_no_arrastra_un_traceback_entero(self) -> None:
        def revienta_largo(*args: object, **kwargs: object) -> None:
            raise OSError("x" * 2000)

        with mock.patch.object(MODULE, "timer_state", revienta_largo):
            MODULE.main(["--today", "2026-08-03"])

        self.assertLess(len(self.enviados[0]), 800)


class MarcadorDePruebaTest(unittest.TestCase):
    """El guardián es un emisor de alertas más: hereda la misma regla que el digest.

    Sin esto, probarlo a mano metía en el canal un aviso indistinguible de uno
    real, que es exactamente lo que se corrigió en el resumen diario.
    """

    def test_un_disparo_manual_se_marca_en_la_primera_linea(self) -> None:
        marcado = MODULE.mark_as_test(MODULE.build_stale_message(dt.date(2026, 7, 30), 3))

        self.assertIn("PRUEBA", marcado.splitlines()[0])

    def test_el_marcado_conserva_el_contenido_del_aviso(self) -> None:
        original = MODULE.build_stale_message(dt.date(2026, 7, 30), 3)
        marcado = MODULE.mark_as_test(original)

        self.assertIn("2026-07-30", marcado)
        self.assertIn("no ha fallado ningún job", marcado)

    def test_desde_systemd_el_aviso_sale_sin_marca(self) -> None:
        enviados: list[str] = []
        carpeta = tempfile.mkdtemp()
        estado = pathlib.Path(carpeta) / "last_day.txt"
        estado.write_text("2026-07-30\n", encoding="utf-8")

        with mock.patch.dict("os.environ", {"INVOCATION_ID": "8f3c"}, clear=False):
            with mock.patch.object(MODULE, "send_telegram", lambda m, e: enviados.append(m)):
                with mock.patch.object(MODULE, "load_env", lambda: dict(CREDENCIALES)):
                    with mock.patch.object(MODULE, "timer_state", lambda run=None: "active"):
                        MODULE.main(["--today", "2026-08-03", "--state-file", str(estado)])

        self.assertNotIn("PRUEBA", enviados[0])

    def test_a_mano_el_aviso_sale_marcado(self) -> None:
        enviados: list[str] = []
        carpeta = tempfile.mkdtemp()
        estado = pathlib.Path(carpeta) / "last_day.txt"
        estado.write_text("2026-07-30\n", encoding="utf-8")

        with mock.patch.dict("os.environ", dict(CREDENCIALES), clear=True):
            with mock.patch.object(MODULE, "send_telegram", lambda m, e: enviados.append(m)):
                with mock.patch.object(MODULE, "timer_state", lambda run=None: "active"):
                    MODULE.main(["--today", "2026-08-03", "--state-file", str(estado)])

        self.assertIn("PRUEBA", enviados[0])


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
