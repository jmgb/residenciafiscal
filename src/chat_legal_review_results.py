"""Compila la revisión jurídica F0.3 después de revelar X/Y."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from chat_legal_review_parsing import parse_review_questions
from chat_legal_review_validation import validate_completed_review

_IDENTITY_FIELDS = ("rubric_version", "rubric_sha256", "dev_set_sha256")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregates(questions: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    strategies = sorted(
        {response["strategy"] for question in questions for response in question["responses"]}
    )
    result: dict[str, dict[str, Any]] = {}
    for strategy in strategies:
        responses = [
            response
            for question in questions
            for response in question["responses"]
            if response["strategy"] == strategy
        ]
        means = [
            response["mean_score"] for response in responses if response["mean_score"] is not None
        ]
        result[strategy] = {
            "response_count": len(responses),
            "safe_count": sum(response["safe"] for response in responses),
            "useful_count": sum(response["useful"] for response in responses),
            "mean_score": round(sum(means) / len(means), 2) if means else None,
            "preferred_count": sum(
                question["preferred_strategy"] == strategy for question in questions
            ),
        }
    return result


def _render_markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# Resultados revelados de la revisión jurídica F0.3",
        "",
        f"**Esquema:** `{result['schema_version']}`.",
        "",
        "## Resumen por estrategia",
        "",
        "| Estrategia | Respuestas | Seguras | Útiles | Media | Preferida |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for strategy, aggregate in result["aggregates"].items():
        lines.append(
            f"| `{strategy}` | {aggregate['response_count']} | {aggregate['safe_count']} | "
            f"{aggregate['useful_count']} | {aggregate['mean_score']} | "
            f"{aggregate['preferred_count']} |"
        )
    lines.extend(["", "## Parejas", ""])
    for question in result["questions"]:
        lines.append(
            f"- `{question['question_id']}`: preferencia `{question['preferred_strategy']}` "
            f"(confianza {question['confidence']})."
        )
    return "\n".join(lines) + "\n"


def compile_review_results(
    *,
    review_path: Path,
    package_path: Path,
    reveal_key_path: Path,
    output_json: Path,
    output_markdown: Path,
    confirm_reveal: bool,
    review_commit: str,
) -> dict[str, Any]:
    if not confirm_reveal:
        raise ValueError("Se requiere confirmación explícita antes de abrir la clave X/Y")
    if re.fullmatch(r"[0-9a-f]{7,64}", review_commit) is None:
        raise ValueError("review_commit debe ser un hash Git hexadecimal")
    inputs = {path.resolve() for path in (review_path, package_path, reveal_key_path)}
    if output_json.resolve() in inputs or output_markdown.resolve() in inputs:
        raise ValueError("Los resultados no pueden sobrescribir los artefactos de entrada")

    package = json.loads(package_path.read_bytes())
    question_ids = [item["question_id"] for item in package["questions"]]
    markdown = review_path.read_text(encoding="utf-8")
    validation = validate_completed_review(markdown, expected_question_ids=question_ids)
    if not validation.valid:
        raise ValueError("La revisión jurídica está incompleta: " + "; ".join(validation.errors))

    reveal = json.loads(reveal_key_path.read_bytes())
    reveal_ids = [item["question_id"] for item in reveal["questions"]]
    if question_ids != reveal_ids or any(
        package.get(field) != reveal.get(field) for field in _IDENTITY_FIELDS
    ):
        raise ValueError("La clave de revelado no coincide con el paquete ciego")
    questions = parse_review_questions(markdown, reveal["questions"])
    result = {
        "schema_version": "residenciafiscal-chat-f03-results/1",
        **{field: package[field] for field in _IDENTITY_FIELDS},
        "review_commit": review_commit,
        "review_sha256": _sha256(review_path),
        "blind_package_sha256": _sha256(package_path),
        "reveal_key_sha256": _sha256(reveal_key_path),
        "questions": questions,
        "aggregates": _aggregates(questions),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_markdown.write_text(_render_markdown(result), encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--package-json", type=Path, required=True)
    parser.add_argument("--reveal-key", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    parser.add_argument("--review-commit", required=True)
    parser.add_argument("--confirm-reveal", action="store_true")
    args = parser.parse_args(argv)
    compile_review_results(
        review_path=args.review,
        package_path=args.package_json,
        reveal_key_path=args.reveal_key,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
        confirm_reveal=args.confirm_reveal,
        review_commit=args.review_commit,
    )
    print(f"Resultados F0.3 compilados: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
