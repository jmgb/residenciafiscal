"""Valida la completitud mecánica de la revisión jurídica ciega F0.3."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DIMENSIONS = (
    "Fidelidad jurídica",
    "Relevancia para la pregunta",
    "Respaldo de fuentes",
    "Cobertura y contraste",
    "Calibración y límites",
    "Claridad y utilidad",
)
INITIAL_FIELDS = (
    "Identificador estable y no personal",
    "Función y cualificación",
    "Experiencia pertinente en fiscalidad y residencia fiscal",
    "Fecha de inicio",
)
INITIAL_DECLARATIONS = (
    "no participé en la generación",
    "desconozco la correspondencia X/Y",
    "no incluiré datos de clientes",
)
CLOSING_DECLARATIONS = (
    "He completado las ",
    "Cada selección contiene una sola opción",
    "He motivado los `N/A`",
    "No abrí material vedado",
    "este formulario queda cerrado",
)


@dataclass(frozen=True)
class ReviewValidationResult:
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def split_sections(markdown: str, level: int) -> tuple[list[str], dict[str, str]]:
    marker = "#" * level
    matches = list(re.finditer(rf"(?m)^{marker} (.+)$", markdown))
    names = [match.group(1).strip() for match in matches]
    bodies = {
        name: markdown[
            match.end() : matches[index + 1].start() if index + 1 < len(matches) else None
        ]
        for index, (name, match) in enumerate(zip(names, matches, strict=True))
    }
    return names, bodies


def line_starting(body: str, prefix: str) -> str | None:
    return next(
        (line.strip() for line in body.splitlines() if line.strip().startswith(prefix)), None
    )


def _selected_count(line: str) -> int:
    return len(re.findall(r"\[[xX]\]", line))


def _validate_choice(errors: list[str], scope: str, line: str | None, choices: int) -> None:
    if line is None:
        errors.append(f"{scope}: falta la selección")
        return
    if len(re.findall(r"\[[ xX]\]", line)) != choices or _selected_count(line) != 1:
        errors.append(f"{scope}: debe haber exactamente una opción marcada")


def _validate_fields(errors: list[str], body: str, scope: str, fields: Sequence[str]) -> None:
    for field in fields:
        line = line_starting(body, f"- {field}:")
        if line is None or not line.partition(":")[2].strip():
            errors.append(f"{scope}/{field}: falta valor")


def _validate_declarations(
    errors: list[str],
    body: str,
    scope: str,
    declarations: Sequence[str],
) -> None:
    for declaration in declarations:
        line = next((value.strip() for value in body.splitlines() if declaration in value), None)
        if line is None or _selected_count(line) != 1:
            errors.append(f"{scope}/{declaration}: falta confirmar")


def _validate_scores(errors: list[str], body: str, scope: str) -> None:
    for dimension in DIMENSIONS:
        match = re.search(
            rf"(?m)^\|\s*{re.escape(dimension)}\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*$",
            body,
        )
        if match is None:
            errors.append(f"{scope}/{dimension}: falta la fila")
            continue
        score, comment = (value.strip() for value in match.groups())
        if score not in {"0", "1", "2", "N/A"}:
            errors.append(f"{scope}/{dimension}: puntuación no válida")
        elif score == "N/A" and not comment:
            errors.append(f"{scope}/{dimension}: N/A exige motivo")


def _validate_response(errors: list[str], body: str, scope: str) -> None:
    for gate in range(1, 6):
        _validate_choice(errors, f"{scope}/G{gate}", line_starting(body, f"- G{gate} "), 3)
    _validate_scores(errors, body, scope)
    critical = line_starting(body, "**Error crítico:**")
    _validate_choice(errors, f"{scope}/error crítico", critical, 2)
    if critical and "[x] sí" in critical.lower():
        observations = body.partition("**Observaciones:**")[2].strip()
        if not observations:
            errors.append(f"{scope}/observaciones: un error crítico exige explicación")


def _validate_pair(errors: list[str], body: str, question_id: str) -> None:
    preference = next(
        (line.strip() for line in body.splitlines() if "empate" in line and "ninguna" in line),
        None,
    )
    _validate_choice(errors, f"{question_id}/preferencia", preference, 4)
    _validate_choice(
        errors,
        f"{question_id}/confianza",
        line_starting(body, "**Confianza:**"),
        3,
    )
    if not body.partition("**Motivo:**")[2].strip():
        errors.append(f"{question_id}/motivo: falta justificar la preferencia")


def validate_completed_review(
    markdown: str,
    *,
    expected_question_ids: Sequence[str],
) -> ReviewValidationResult:
    errors: list[str] = []
    headings, sections = split_sections(markdown, 2)
    expected_headings = [
        "Declaración inicial del revisor jurídico",
        *expected_question_ids,
        "Declaración de cierre",
    ]
    if headings != expected_headings:
        errors.append("preguntas: el formulario no contiene exactamente los IDs esperados en orden")

    initial = sections.get("Declaración inicial del revisor jurídico", "")
    _validate_fields(errors, initial, "declaración inicial", INITIAL_FIELDS)
    _validate_declarations(errors, initial, "declaración inicial", INITIAL_DECLARATIONS)

    for question_id in expected_question_ids:
        body = sections.get(question_id, "")
        subsection_names, subsections = split_sections(body, 3)
        if subsection_names != ["Respuesta X", "Respuesta Y", "Preferencia de la pareja"]:
            errors.append(f"{question_id}: faltan las dos respuestas o la preferencia")
            continue
        _validate_response(errors, subsections["Respuesta X"], f"{question_id}/X")
        _validate_response(errors, subsections["Respuesta Y"], f"{question_id}/Y")
        _validate_pair(errors, subsections["Preferencia de la pareja"], question_id)

    closing = sections.get("Declaración de cierre", "")
    _validate_fields(errors, closing, "declaración de cierre", ("Fecha de cierre",))
    _validate_declarations(errors, closing, "declaración de cierre", CLOSING_DECLARATIONS)
    return ReviewValidationResult(errors=tuple(errors))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--package-json", type=Path, required=True)
    args = parser.parse_args(argv)
    package = json.loads(args.package_json.read_bytes())
    question_ids = tuple(item["question_id"] for item in package["questions"])
    result = validate_completed_review(
        args.review.read_text(encoding="utf-8"),
        expected_question_ids=question_ids,
    )
    if result.valid:
        print("Revisión jurídica F0.3 completa")
        return 0
    for error in result.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
