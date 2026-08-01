"""Tests de contrato para la retención y supresión del dato conversacional."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
MIGRATION_GLOB = "supabase/migrations/*_chat_privacy_retention_and_deletion.sql"
PRIVACY_DIR = PROJECT_ROOT / "scripts" / "privacy"


def migration_text() -> str:
    migrations = sorted(PROJECT_ROOT.glob(MIGRATION_GLOB))
    assert len(migrations) == 1, migrations
    return migrations[0].read_text("utf-8")


def test_la_migracion_separa_fallos_de_peticiones_completadas() -> None:
    sql = migration_text()

    assert "'failed'" in sql
    assert "'timed_out'" in sql
    assert "failure_code" in sql
    assert "fail_chat_request" in sql


def test_la_migracion_expone_las_operaciones_privadas_de_ciclo_de_vida() -> None:
    sql = "\n".join(
        path.read_text("utf-8")
        for path in sorted(PROJECT_ROOT.glob("supabase/migrations/*_chat_*.sql"))
    )

    assert "purge_expired_chat_data" in sql
    assert "delete_chat_conversation" in sql
    assert "p_cutoff timestamptz" in sql
    assert "DELETE FROM private.chat_requests" in sql
    assert "REVOKE ALL ON FUNCTION private.delete_chat_conversation" in sql


def test_el_purgado_tiene_dry_run_limite_y_auditoria() -> None:
    sql = "\n".join(
        path.read_text("utf-8")
        for path in sorted(PROJECT_ROOT.glob("supabase/migrations/*_chat_*.sql"))
    )

    assert "chat_retention_purge_audit" in sql
    assert "p_dry_run boolean" in sql
    assert "p_batch_limit integer" in sql
    assert "batch_overflow" in sql
    assert "dry_run" in sql


def test_la_supresion_bloquea_la_conversacion_y_la_fk_del_presupuesto_tiene_indice() -> None:
    sql = "\n".join(
        path.read_text("utf-8")
        for path in sorted(PROJECT_ROOT.glob("supabase/migrations/*_chat_privacy*.sql"))
    )

    assert "FOR UPDATE" in sql
    assert "chat_requests_budget_date_idx" in sql


def test_la_automatizacion_exige_retencion_explicita_y_no_muestra_contenido() -> None:
    purge = (PRIVACY_DIR / "purge-chat-data.sh").read_text("utf-8")

    assert "CHAT_RETENTION_DAYS" in purge
    assert "CHAT_RETENTION_PURGE_ENABLED" in purge
    assert "CHAT_RETENTION_DRY_RUN" in purge
    assert "CHAT_RETENTION_BATCH_LIMIT" in purge
    assert ':-false' in purge
    assert ':-true' in purge
    assert "Falta CHAT_RETENTION_DAYS" in purge
    assert "content" not in purge.lower()


def test_la_supresion_operativa_exige_ticket_y_confirmacion() -> None:
    deletion = (PRIVACY_DIR / "delete-chat-conversation.sh").read_text("utf-8")

    assert "--ticket" in deletion
    assert "--confirm-delete" in deletion
    assert "private.delete_chat_conversation" in deletion
    assert "UUID" in deletion or "identidad" in deletion


def test_el_timer_de_retencion_es_persistente_y_se_instala_por_separado() -> None:
    service = (PRIVACY_DIR / "residenciafiscal-chat-retention.service").read_text("utf-8")
    timer = (PRIVACY_DIR / "residenciafiscal-chat-retention.timer").read_text("utf-8")
    installer = (PRIVACY_DIR / "install-chat-retention-timer.sh").read_text("utf-8")

    assert "ExecStart=/bin/bash" in service
    assert "OnFailure=residenciafiscal-backup-failure@%n.service" in service
    assert "Persistent=true" in timer
    assert "CHAT_RETENTION_DAYS" in installer


def test_los_backups_pueden_acompasarse_al_plazo_del_chat() -> None:
    backup = (PROJECT_ROOT / "scripts/backup/vps-backup.sh").read_text("utf-8")

    assert "BACKUP_RETENTION_DAYS" in backup
    assert "CHAT_RETENTION_DAYS" in backup
    assert "${BACKUP_RETENTION_DAYS:-${CHAT_RETENTION_DAYS:-30}}" in backup
