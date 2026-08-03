from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = PROJECT_ROOT / "supabase/migrations/20260803123000_deep_research_comparison_votes.sql"


def migration_text() -> str:
    return MIGRATION.read_text("utf-8")


def test_la_ampliacion_de_rpc_conserva_la_firma_anterior_durante_el_deploy() -> None:
    sql = migration_text()

    assert "DROP FUNCTION public.create_deep_research_job(text, text, text, text, text)" not in sql
    assert "p_comparison_id => NULL" in sql
    assert "public.create_deep_research_job(text, text, text, text, text)" in sql


def test_la_comparacion_debe_pertenecer_a_la_misma_conversacion_pais_y_pregunta() -> None:
    sql = migration_text()

    assert "requests.conversation_id = p_conversation_id" in sql
    assert "requests.country_path = p_country_path" in sql
    assert "messages.content = trim(p_question)" in sql


def test_un_voto_c_exige_una_investigacion_profunda_completada() -> None:
    sql = migration_text()

    assert "p_verdict <> 'c'" in sql
    assert "jobs.comparison_id = p_request_id" in sql
    assert "jobs.status = 'completed'" in sql
