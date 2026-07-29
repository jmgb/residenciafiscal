"""Validación determinista de perfiles experimentales producidos por agente."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_profile_validation import validate_agent_profile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPOSITORY_ROOT / "experiments" / "okf-agent" / "san-1071-2025.agent.md"


def test_valida_los_extractos_del_agente_contra_el_pdf() -> None:
    result = validate_agent_profile(PROFILE_PATH)

    assert result.pdf_page_count == 6
    assert result.source_excerpt_count == 7
    assert result.source_sha256 == (
        "43be81687f4871186c1c34a3c2a97166fc64753662d4d4914bf03c466873c3cf"
    )


def test_rechaza_un_extracto_del_agente_reescrito(tmp_path: Path) -> None:
    profile = PROFILE_PATH.read_text(encoding="utf-8").replace(
        "La cuestión esencial consiste si el recurrente es o no trabajador trasfronterizo.",
        "La cuestión principal es determinar la residencia fiscal.",
        1,
    )
    copied_profile = tmp_path / "san-1071-2025.agent.md"
    copied_profile.write_text(profile, encoding="utf-8")

    with pytest.raises(ValueError, match="no es literal"):
        validate_agent_profile(copied_profile, repository_root=REPOSITORY_ROOT)
