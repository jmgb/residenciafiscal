"""Gate del subsistema de backup (`scripts/backup/`).

Los scripts corren en el VPS, fuera de cualquier suite: si una unit apunta a un
fichero que ya no existe o el instalador se olvida de copiar una, nadie se entera
hasta que falta un backup. Presupuestor pagó dos veces esa factura —un
`status=203/EXEC` diario y un `status=127` que tumbó los tres jobs a la vez— y
este fichero convierte ambas cicatrices en aserciones.

Lo que aquí se comprueba es estructura, no comportamiento: que las piezas se
apuntan entre sí. Que el backup funcione de verdad lo dicen el timer de frescura
y el simulacro mensual documentados en `docs/operations/BACKUPS.md`.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
BACKUP_DIR = PROJECT_ROOT / "scripts" / "backup"
SUPABASE_CHAT_DOC = PROJECT_ROOT / "docs" / "operations" / "SUPABASE_CHAT.md"

# Ruta del checkout en el VPS, tal y como la escriben las units de systemd.
VPS_CHECKOUT = "/home/ubuntu/residenciafiscal"

# Scripts que hablan con R2 y por tanto necesitan la región "auto" (R2 responde
# HeadObject 400 con cualquier otra, y el .env del VPS define otras variables AWS).
R2_SCRIPTS = (
    "vps-backup.sh",
    "check-backup-freshness.sh",
    "check-backup-restore-drill.sh",
    "restore-from-r2.sh",
)

EXEC_START = re.compile(r"^ExecStart=/bin/bash (?P<ruta>\S+)$", re.MULTILINE)
ON_FAILURE = re.compile(r"^OnFailure=(?P<unit>\S+)$", re.MULTILINE)

# `| `private.chat_messages` |` en las tablas de SUPABASE_CHAT.md. Se exige
# snake_case en ambos lados para no confundir un `TASKS.md` con un schema.
TABLA_CUALIFICADA = re.compile(r"`(?P<schema>[a-z][a-z0-9_]*)\.(?P<tabla>[a-z][a-z0-9_]*)`")


def units() -> list[Path]:
    return sorted(p for p in BACKUP_DIR.iterdir() if p.suffix in {".service", ".timer"})


def scripts() -> list[Path]:
    return sorted(BACKUP_DIR.glob("*.sh"))


def test_el_directorio_tiene_las_piezas_esperadas() -> None:
    """Autocomprobación: si esto falla, el resto de tests no está mirando nada."""
    nombres = {p.name for p in BACKUP_DIR.iterdir()}

    assert "vps-backup.sh" in nombres
    assert "install-backup-timer.sh" in nombres
    assert len(units()) == 7, sorted(nombres)


def test_cada_execstart_apunta_a_un_script_existente() -> None:
    """Una unit que apunta a un fichero borrado falla con 203/EXEC, no al instalar."""
    for unit in units():
        for match in EXEC_START.finditer(unit.read_text("utf-8")):
            ruta = match.group("ruta")
            assert ruta.startswith(f"{VPS_CHECKOUT}/scripts/backup/"), f"{unit.name}: {ruta}"
            destino = PROJECT_ROOT / ruta.removeprefix(f"{VPS_CHECKOUT}/")
            assert destino.is_file(), f"{unit.name} apunta a {ruta}, que no existe en el repo"


def test_las_units_se_ejecutan_via_bash() -> None:
    """El bit executable se pierde en un checkout; `/bin/bash <script>` no depende de él."""
    for unit in units():
        contenido = unit.read_text("utf-8")
        for linea in contenido.splitlines():
            if linea.startswith("ExecStart="):
                assert linea.startswith("ExecStart=/bin/bash "), f"{unit.name}: {linea}"


def test_el_instalador_copia_todas_las_units_del_directorio() -> None:
    """Una unit nueva que el instalador no lista nunca llega al VPS."""
    instalador = (BACKUP_DIR / "install-backup-timer.sh").read_text("utf-8")

    for unit in units():
        assert unit.name in instalador, f"{unit.name} no aparece en install-backup-timer.sh"


def test_el_instalador_activa_todos_los_timers() -> None:
    timers = [u.name for u in units() if u.suffix == ".timer"]
    bloque = (BACKUP_DIR / "install-backup-timer.sh").read_text("utf-8")
    bloque_timers = bloque.split("TIMERS=(")[1].split(")")[0]

    for timer in timers:
        assert timer in bloque_timers, f"{timer} no se activa en el instalador"


def test_ningun_script_ejecuta_el_env() -> None:
    """`source .env` rompe con cualquier valor con espacios sin comillas.

    Es el incidente del 2026-07-01 en Presupuestor: `NOMBRE=Miguel de Presupuestor`
    hizo que bash intentara ejecutar `de Presupuestor` y los tres jobs murieron con
    exit 127 el mismo día. Las claves se leen con `lib-read-env.sh`, que parsea sin
    ejecutar.
    """
    prohibido = re.compile(r"^\s*(source|\.)\s+.*ENV_FILE", re.MULTILINE)

    for script in scripts():
        contenido = script.read_text("utf-8")
        assert not prohibido.search(contenido), f"{script.name} hace source del .env"
        # Lo único que se puede `source`ar es el helper compartido.
        for match in re.finditer(r"^\s*source\s+(?P<obj>\S+)", contenido, re.MULTILINE):
            assert "lib-read-env.sh" in match.group("obj"), f"{script.name}: {match.group('obj')}"


def test_los_scripts_de_r2_fijan_la_region_auto() -> None:
    """R2 solo acepta `auto`; sin fijarla, una variable AWS del .env da HeadObject 400."""
    for nombre in R2_SCRIPTS:
        contenido = (BACKUP_DIR / nombre).read_text("utf-8")
        assert 'AWS_DEFAULT_REGION="auto"' in contenido, nombre


def test_los_servicios_notifican_sus_fallos() -> None:
    """Un backup que falla en silencio no es un backup.

    La plantilla `@.service` recibe la unit que falló en `%i`, así que cubre también
    los fallos que el script no puede notificar por sí mismo: timeout, OOM, 203/EXEC.
    """
    plantilla = "residenciafiscal-backup-failure@%n.service"

    for unit in units():
        if unit.suffix != ".service" or unit.name.endswith("@.service"):
            continue
        declarados = ON_FAILURE.findall(unit.read_text("utf-8"))
        assert declarados == [plantilla], f"{unit.name}: OnFailure={declarados}"


def test_cada_timer_tiene_su_servicio_y_sobrevive_a_un_reinicio() -> None:
    """`Persistent=true` recupera la ejecución perdida si el VPS estaba apagado."""
    for timer in (u for u in units() if u.suffix == ".timer"):
        servicio = timer.with_suffix(".service")
        assert servicio.is_file(), f"{timer.name} no tiene servicio hermano"
        assert "Persistent=true" in timer.read_text("utf-8"), timer.name


def test_todos_los_scripts_comparten_el_mismo_bucket_por_defecto() -> None:
    """Un bucket distinto en el check de frescura vigilaría un destino vacío."""
    buckets = set()
    for nombre in R2_SCRIPTS:
        contenido = (BACKUP_DIR / nombre).read_text("utf-8")
        match = re.search(r"BACKUP_R2_BUCKET:-(?P<bucket>[\w-]+)\}", contenido)
        assert match, f"{nombre} no declara bucket por defecto"
        buckets.add(match.group("bucket"))

    assert buckets == {"residenciafiscal-backup"}, buckets


def schemas_declarados_en_el_dump() -> list[str]:
    contenido = (BACKUP_DIR / "vps-backup.sh").read_text("utf-8")
    bloque = contenido.split("BACKUP_SCHEMAS=(")[1].split(")")[0]
    return bloque.split()


def test_el_dump_cubre_el_schema_donde_vive_el_dato_del_chat() -> None:
    """El chat persiste en `private`, no en `public`.

    Copiar el `--schema=public --schema=auth` de Presupuestor habría dejado fuera
    las cuatro tablas del chat sin que ningún check se quejara: el objeto se sube,
    el gzip es válido y el backup sale verde.
    """
    assert "private" in schemas_declarados_en_el_dump()


def test_el_dump_cubre_todos_los_schemas_del_contrato_de_persistencia() -> None:
    """Cruce con `SUPABASE_CHAT.md`: si el contrato crece, el dump lo sigue.

    El documento se salta la comprobación si aún no existe —llega con el trabajo
    de persistencia del chat—, pero el schema `private` ya está atado en el test
    anterior, así que no hay ventana sin gate.
    """
    if not SUPABASE_CHAT_DOC.is_file():
        return

    declarados = schemas_declarados_en_el_dump()
    doc = SUPABASE_CHAT_DOC.read_text("utf-8")

    for schema in sorted({m.group("schema") for m in TABLA_CUALIFICADA.finditer(doc)}):
        assert schema in declarados, (
            f"SUPABASE_CHAT.md usa el schema `{schema}` y vps-backup.sh no lo dumpea"
        )


def _dump_sql_de_prueba() -> str:
    return """\
-- Residencia Fiscal Full Backup
-- Timestamp: 2026-08-01_120000
-- Project: proyecto-de-prueba
-- Schemas: public private auth supabase_migrations
-- Application tables: private.chat_conversations private.chat_messages
-- Required public functions: public.complete_chat_request public.create_chat_request public.fail_chat_request

CREATE TABLE private.chat_conversations (
    id uuid NOT NULL
);
CREATE TABLE private.chat_messages (
    id uuid NOT NULL
);
CREATE FUNCTION public.complete_chat_request() RETURNS void
    LANGUAGE sql AS $$ SELECT; $$;
CREATE FUNCTION public.create_chat_request() RETURNS void
    LANGUAGE sql AS $$ SELECT; $$;
CREATE FUNCTION public.fail_chat_request() RETURNS void
    LANGUAGE sql AS $$ SELECT; $$;
COPY private.chat_conversations (id) FROM stdin;
\\.
COPY private.chat_messages (id) FROM stdin;
\\.
"""


def _ejecutar_verificador(sql_file: Path, **env: str) -> subprocess.CompletedProcess[str]:
    verifier = BACKUP_DIR / "verify-backup-contract.sh"
    return subprocess.run(
        ["/bin/bash", str(verifier), str(sql_file)],
        cwd=PROJECT_ROOT,
        env={**os.environ, **env},
        text=True,
        capture_output=True,
        check=False,
    )


def test_el_verificador_acepta_un_dump_coherente(tmp_path: Path) -> None:
    sql_file = tmp_path / "backup.sql"
    sql_file.write_text(_dump_sql_de_prueba(), "utf-8")

    resultado = _ejecutar_verificador(
        sql_file,
        BACKUP_EXPECTED_PROJECT="proyecto-de-prueba",
        BACKUP_EXPECTED_SCHEMAS="public private auth supabase_migrations",
        BACKUP_EXPECTED_APPLICATION_TABLES=("private.chat_conversations private.chat_messages"),
        BACKUP_EXPECTED_PUBLIC_FUNCTIONS=(
            "public.complete_chat_request public.create_chat_request public.fail_chat_request"
        ),
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "Backup contract OK" in resultado.stdout


def test_el_verificador_detecta_una_tabla_sin_datos_restaurables(tmp_path: Path) -> None:
    sql_file = tmp_path / "backup.sql"
    sql_file.write_text(
        _dump_sql_de_prueba().replace("COPY private.chat_messages (id) FROM stdin;\n\\.\n", ""),
        "utf-8",
    )

    resultado = _ejecutar_verificador(sql_file)

    assert resultado.returncode != 0
    assert "COPY private.chat_messages" in resultado.stderr


def test_el_verificador_compara_el_inventario_con_supabase(tmp_path: Path) -> None:
    sql_file = tmp_path / "backup.sql"
    sql_file.write_text(_dump_sql_de_prueba(), "utf-8")

    resultado = _ejecutar_verificador(
        sql_file,
        BACKUP_EXPECTED_APPLICATION_TABLES=(
            "private.chat_conversations private.chat_messages private.chat_requests"
        ),
    )

    assert resultado.returncode != 0
    assert "Application tables" in resultado.stderr


def test_el_verificador_rechaza_ddl_ejecutable_del_presupuesto_antiguo(
    tmp_path: Path,
) -> None:
    sql_file = tmp_path / "backup.sql"
    sql_file.write_text(
        _dump_sql_de_prueba()
        + "\nCREATE FUNCTION public.reserve_chat_request() RETURNS void LANGUAGE sql AS $$ SELECT; $$;\n",
        "utf-8",
    )

    resultado = _ejecutar_verificador(sql_file)

    assert resultado.returncode != 0
    assert "objeto económico prohibido" in resultado.stderr


def test_el_verificador_tolera_el_historial_literal_de_migraciones(tmp_path: Path) -> None:
    sql_file = tmp_path / "backup.sql"
    sql_file.write_text(
        _dump_sql_de_prueba()
        + "\nCOPY supabase_migrations.schema_migrations (version, statements) FROM stdin;\n"
        + '20260731\t{"CREATE TABLE private.chat_daily_budgets"}\n'
        + "\\.\n",
        "utf-8",
    )

    resultado = _ejecutar_verificador(sql_file)

    assert resultado.returncode == 0, resultado.stderr


def test_backup_y_checks_reutilizan_el_verificador_de_contrato() -> None:
    for nombre in (
        "vps-backup.sh",
        "check-backup-freshness.sh",
        "restore-from-r2.sh",
    ):
        contenido = (BACKUP_DIR / nombre).read_text("utf-8")
        assert "verify-backup-contract.sh" in contenido, nombre


def test_el_simulacro_compara_con_el_inventario_vivo_de_supabase() -> None:
    contenido = (BACKUP_DIR / "check-backup-restore-drill.sh").read_text("utf-8")

    assert "SUPABASE_DB_PASSWORD" in contenido
    assert "SUPABASE_REF" in contenido
    assert "BACKUP_VERIFY_LIVE_CONTRACT=1" in contenido
