"""Contrato estático: el coste observado nunca controla la admisión del chat."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


def test_no_existe_el_breaker_monetario_prohibido() -> None:
    forbidden = list(
        PROJECT_ROOT.glob("supabase/migrations/*_chat_budget_circuit_breaker.sql")
    ) + list(PROJECT_ROOT.glob("supabase/tests/*chat_budget_circuit*"))

    assert forbidden == []


def test_la_migracion_vigente_restaura_solo_observabilidad() -> None:
    migrations = sorted(
        PROJECT_ROOT.glob("supabase/migrations/*_restore_chat_observability_only.sql")
    )
    assert len(migrations) == 1, migrations
    sql = migrations[0].read_text("utf-8")

    assert "DROP TABLE IF EXISTS private.chat_daily_budgets" in sql
    assert "DROP TABLE IF EXISTS private.chat_budget_policy" in sql
    assert "DROP COLUMN IF EXISTS reservation_microusd" in sql
    assert "'request_id', v_request_id" in sql
    assert "'allowed', false" not in sql
    assert "coste observado" in sql


def test_la_function_no_decide_por_coste_observado() -> None:
    source = "\n".join(
        (
            (PROJECT_ROOT / "frontend/netlify/functions/chat/chat.ts").read_text("utf-8"),
            (PROJECT_ROOT / "frontend/netlify/functions/chat/supabase-chat-store.ts").read_text(
                "utf-8"
            ),
            (PROJECT_ROOT / "frontend/netlify/functions/chat/composition.ts").read_text("utf-8"),
        )
    )

    assert "reservation_microusd" not in source
    assert "Presupuesto diario agotado" not in source
    assert "CHAT_DAILY_BUDGET_USD" not in source
    assert "CHAT_REQUEST_RESERVATION_USD" not in source
