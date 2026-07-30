"""Interpreta un formulario F0.3 que ya superó la validación mecánica."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from chat_legal_review_validation import DIMENSIONS, line_starting, split_sections

_KEY_DIMENSIONS = {
    "Fidelidad jurídica",
    "Relevancia para la pregunta",
    "Respaldo de fuentes",
}


def _selected(line: str, options: Sequence[str]) -> str:
    for option in options:
        if re.search(rf"\[[xX]\]\s*{re.escape(option)}(?:\s|$)", line, re.IGNORECASE):
            return option
    raise ValueError(f"No se pudo interpretar una selección validada: {line}")


def _parse_response(body: str, *, label: str, strategy: str) -> dict[str, Any]:
    gates = {
        f"G{gate}": _selected(
            line_starting(body, f"- G{gate} ") or "",
            ("pasa", "falla", "N/A"),
        )
        for gate in range(1, 6)
    }
    scores: dict[str, int | None] = {}
    for dimension in DIMENSIONS:
        match = re.search(rf"(?m)^\|\s*{re.escape(dimension)}\s*\|\s*([^|]*)\|", body)
        raw_score = match.group(1).strip() if match else "N/A"
        scores[dimension] = None if raw_score == "N/A" else int(raw_score)
    critical_line = line_starting(body, "**Error crítico:**") or ""
    critical_error = _selected(critical_line, ("no", "sí")) == "sí"
    applicable = [score for score in scores.values() if score is not None]
    mean_score = round(sum(applicable) / len(applicable), 2) if applicable else None
    safe = all(value in {"pasa", "N/A"} for value in gates.values()) and not critical_error
    useful = (
        safe
        and all(scores[dimension] != 0 for dimension in _KEY_DIMENSIONS)
        and mean_score is not None
        and mean_score >= 1.5
    )
    return {
        "label": label,
        "strategy": strategy,
        "safe": safe,
        "useful": useful,
        "mean_score": mean_score,
        "critical_error": critical_error,
        "gates": gates,
        "scores": scores,
    }


def parse_review_questions(
    markdown: str,
    mappings: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    _, question_sections = split_sections(markdown, 2)
    parsed: list[dict[str, Any]] = []
    for mapping in mappings:
        question_id = mapping["question_id"]
        _, subsections = split_sections(question_sections[question_id], 3)
        responses = [
            _parse_response(
                subsections[f"Respuesta {label}"],
                label=label,
                strategy=mapping[f"{label.lower()}_strategy"],
            )
            for label in ("X", "Y")
        ]
        preference_body = subsections["Preferencia de la pareja"]
        preference_line = next(
            line for line in preference_body.splitlines() if "empate" in line and "ninguna" in line
        )
        preference = _selected(preference_line, ("X", "Y", "empate", "ninguna"))
        confidence = _selected(
            line_starting(preference_body, "**Confianza:**") or "",
            ("baja", "media", "alta"),
        )
        preferred_strategy = (
            mapping[f"{preference.lower()}_strategy"] if preference in {"X", "Y"} else preference
        )
        parsed.append(
            {
                "question_id": question_id,
                "responses": responses,
                "preference": preference,
                "preferred_strategy": preferred_strategy,
                "confidence": confidence,
            }
        )
    return parsed
