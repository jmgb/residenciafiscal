from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = PROJECT_ROOT / "supabase/migrations/20260803203000_deep_research_assistant_messages.sql"
PRICING_VERSION_MIGRATION = (
    PROJECT_ROOT / "supabase/migrations/20260804140000_deep_research_pricing_version.sql"
)


def migration_sql() -> str:
    assert MIGRATION.exists(), MIGRATION
    return MIGRATION.read_text("utf-8")


def test_deep_research_result_is_an_idempotent_assistant_message() -> None:
    sql = migration_sql()

    assert "ADD COLUMN deep_research_job_id text" in sql
    assert "REFERENCES private.deep_research_jobs(job_id) ON DELETE CASCADE" in sql
    assert "'deep_research'" in sql
    assert "INSERT INTO private.chat_messages" in sql
    assert "'assistant'" in sql
    assert "v_job.result->>'text'" in sql
    assert "ON CONFLICT (deep_research_job_id)" in sql


def test_deep_research_messages_do_not_change_the_ab_request_ledger() -> None:
    sql = migration_sql()

    assert "DROP INDEX private.chat_messages_one_answer_per_strategy" not in sql
    assert "AND request_id IS NULL" in sql
    assert "v_job.comparison_id," not in sql


def test_deep_research_message_preserves_evidence_claims_and_measurement() -> None:
    sql = migration_sql()

    assert "v_job.result->'evidence'" in sql
    assert "v_job.result->'claims'" in sql
    assert "v_job.result->'limits'" in sql
    assert "v_job.result->>'costMeasurement'" in sql
    assert "v_job.result->>'costMicrousd'" in sql
    assert "v_job.result->>'latencyMs'" in sql
    assert "v_job.result->>'reasoningEffort'" in sql


def test_deep_research_update_remains_backend_only() -> None:
    sql = migration_sql()

    assert "CREATE OR REPLACE FUNCTION public.update_deep_research_job" in sql
    assert "SECURITY DEFINER" in sql
    assert "SET search_path = pg_catalog, private" in sql
    assert "FROM PUBLIC, anon, authenticated" in sql
    assert "TO service_role" in sql


def test_deep_research_message_persists_and_backfills_pricing_version() -> None:
    assert PRICING_VERSION_MIGRATION.exists(), PRICING_VERSION_MIGRATION
    sql = PRICING_VERSION_MIGRATION.read_text("utf-8")

    assert "pricing_version" in sql
    assert "v_job.result->>'pricingVersion'" in sql
    assert "m.deep_research_job_id = j.job_id" in sql
