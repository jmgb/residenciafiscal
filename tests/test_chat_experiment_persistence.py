from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_GLOB = "supabase/migrations/*_chat_experiment_ledger.sql"


def _migration_sql() -> str:
    migrations = sorted(PROJECT_ROOT.glob(MIGRATION_GLOB))
    assert len(migrations) == 1, migrations
    return migrations[0].read_text("utf-8")


def test_ledger_persiste_version_del_experimento_y_diagnosticos_por_estrategia() -> None:
    sql = _migration_sql()

    assert "ADD COLUMN experiment jsonb" in sql
    assert "ADD COLUMN claims jsonb" in sql
    assert "ADD COLUMN diagnostics jsonb" in sql
    assert "p_experiment jsonb" in sql
    assert "answer->'claims'" in sql
    assert "answer->'diagnostics'" in sql


def test_ledger_sigue_siendo_privado_y_la_rpc_solo_es_backend() -> None:
    sql = _migration_sql()

    assert "REVOKE ALL ON FUNCTION public.create_chat_request" in sql
    assert "FROM PUBLIC, anon, authenticated" in sql
    assert "TO service_role" in sql
