"""Contrato de persistencia del esfuerzo de razonamiento del chat."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


def test_la_migracion_guarda_el_reasoning_effort_de_cada_respuesta() -> None:
    sql = "\n".join(
        path.read_text("utf-8")
        for path in sorted(PROJECT_ROOT.glob("supabase/migrations/*_chat_*.sql"))
    )

    assert "ADD COLUMN reasoning_effort text" in sql
    assert "answer->>'reasoning_effort'" in sql
    assert "COMMENT ON COLUMN private.chat_messages.reasoning_effort" in sql
