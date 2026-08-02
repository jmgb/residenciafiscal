from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_GLOB = "supabase/migrations/*_chat_comparison_votes.sql"


def test_voto_es_privado_unico_y_sin_texto_libre() -> None:
    migrations = sorted(PROJECT_ROOT.glob(MIGRATION_GLOB))
    assert len(migrations) == 1, migrations
    sql = migrations[0].read_text("utf-8")

    assert "CREATE TABLE private.chat_comparison_votes" in sql
    assert "request_id text PRIMARY KEY" in sql
    assert "verdict text NOT NULL" in sql
    assert "reason text NOT NULL" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "REVOKE ALL ON TABLE private.chat_comparison_votes" in sql
    assert "CREATE FUNCTION public.record_chat_vote" in sql
    assert "TO service_role" in sql
