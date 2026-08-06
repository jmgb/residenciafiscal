from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260806015000_chat_history_possession.sql"


def test_history_requires_a_hashed_conversation_secret():
    sql = MIGRATION.read_text("utf-8")

    assert "conversation_access_hash" in sql
    assert "ADD COLUMN IF NOT EXISTS conversation_access_hash" in sql
    assert "DROP FUNCTION IF EXISTS public.read_chat_history(text, integer)" in sql
    assert "p_conversation_access_hash text" in sql
    assert "read_chat_history(text, text, integer)" in sql
    assert "c.conversation_access_hash = p_conversation_access_hash" in sql
    assert "GRANT EXECUTE ON FUNCTION public.read_chat_history(text, text, integer)" in sql
