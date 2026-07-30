"""Construcción determinista del paquete ciego de evaluación F0.3."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from chat_strategy_models import (
    AnswerStatus,
    ComparisonReport,
    StrategyAnswer,
    StrategyId,
)
from jurisprudence_case_catalogs import (
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)

BlindLabel = Literal["X", "Y"]


class ArtifactProvenance(JurisprudenceCaseModel):
    path: NonEmptyText
    sha256: Sha256


class BlindSource(JurisprudenceCaseModel):
    judgment_id: NonEmptyText
    page: int = Field(gt=0)
    quote: NonEmptyText
    verification: Literal["EXACT"]


class BlindResponse(JurisprudenceCaseModel):
    label: BlindLabel
    status: AnswerStatus
    text: str
    limits: tuple[str, ...]
    sources: tuple[BlindSource, ...]


class BlindQuestion(JurisprudenceCaseModel):
    question_id: NonEmptyText
    question: NonEmptyText
    intent: NonEmptyText
    responses: tuple[BlindResponse, BlindResponse]


class BlindReviewPackage(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-chat-f03-blind-review/1"] = (
        "residenciafiscal-chat-f03-blind-review/1"
    )
    rubric_version: NonEmptyText
    rubric_sha256: Sha256
    dev_set_sha256: Sha256
    blind: Literal[True] = True
    questions: tuple[BlindQuestion, ...]


class RevealQuestion(JurisprudenceCaseModel):
    question_id: NonEmptyText
    x_strategy: StrategyId
    y_strategy: StrategyId
    artifact_path: NonEmptyText
    artifact_sha256: Sha256


class BlindRevealKey(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-chat-f03-reveal-key/1"] = (
        "residenciafiscal-chat-f03-reveal-key/1"
    )
    rubric_version: NonEmptyText
    rubric_sha256: Sha256
    dev_set_sha256: Sha256
    questions: tuple[RevealQuestion, ...]


def _other_strategy(strategy: StrategyId) -> StrategyId:
    if strategy == "current_structured":
        return "gemini_file_search"
    return "current_structured"


def _answer_by_strategy(
    report: ComparisonReport,
    strategy: StrategyId,
) -> StrategyAnswer:
    return next(answer for answer in report.answers if answer.strategy == strategy)


def _blind_response(answer: StrategyAnswer, label: BlindLabel) -> BlindResponse:
    status = answer.status
    text = answer.text
    limits = answer.limits
    sources = answer.sources
    if status in {"completa", "parcial"} and text and not sources:
        status = "error"
        text = ""
        limits = (
            "La respuesta sustantiva fue retirada porque no quedó ninguna fuente verificable.",
            *limits,
        )
    return BlindResponse(
        label=label,
        status=status,
        text=text,
        limits=limits,
        sources=tuple(
            BlindSource(
                judgment_id=source.judgment_id,
                page=source.page,
                quote=source.quote,
                verification=source.verification,
            )
            for source in sources
        ),
    )


def build_blind_review_package(
    *,
    dev_set: dict[str, Any],
    comparisons: Mapping[str, ComparisonReport],
    intents: Mapping[str, str],
    x_strategies: Mapping[str, StrategyId],
    provenance: Mapping[str, ArtifactProvenance],
    rubric_version: str,
    rubric_sha256: str,
    dev_set_sha256: str,
) -> tuple[BlindReviewPackage, BlindRevealKey]:
    question_ids = tuple(item["question_id"] for item in dev_set["questions"])
    expected = set(question_ids)
    for name, values in (
        ("comparisons", comparisons),
        ("intents", intents),
        ("x_strategies", x_strategies),
        ("provenance", provenance),
    ):
        if set(values) != expected:
            raise ValueError(f"{name} no cubre exactamente las preguntas del banco")

    structured_x = sum(strategy == "current_structured" for strategy in x_strategies.values())
    file_search_x = len(x_strategies) - structured_x
    if abs(structured_x - file_search_x) > 1:
        raise ValueError("El orden X/Y debe estar equilibrado entre estrategias")

    questions: list[BlindQuestion] = []
    reveal_questions: list[RevealQuestion] = []
    for item in dev_set["questions"]:
        question_id = item["question_id"]
        x_strategy = x_strategies[question_id]
        y_strategy = _other_strategy(x_strategy)
        report = comparisons[question_id]
        questions.append(
            BlindQuestion(
                question_id=question_id,
                question=item["question"],
                intent=intents[question_id],
                responses=(
                    _blind_response(
                        _answer_by_strategy(report, x_strategy),
                        "X",
                    ),
                    _blind_response(
                        _answer_by_strategy(report, y_strategy),
                        "Y",
                    ),
                ),
            )
        )
        artifact = provenance[question_id]
        reveal_questions.append(
            RevealQuestion(
                question_id=question_id,
                x_strategy=x_strategy,
                y_strategy=y_strategy,
                artifact_path=artifact.path,
                artifact_sha256=artifact.sha256,
            )
        )

    return (
        BlindReviewPackage(
            rubric_version=rubric_version,
            rubric_sha256=rubric_sha256,
            dev_set_sha256=dev_set_sha256,
            questions=tuple(questions),
        ),
        BlindRevealKey(
            rubric_version=rubric_version,
            rubric_sha256=rubric_sha256,
            dev_set_sha256=dev_set_sha256,
            questions=tuple(reveal_questions),
        ),
    )


def _resolve(project_root: Path, relative_path: str) -> Path:
    root = project_root.resolve()
    path = (root / relative_path).resolve()
    path.relative_to(root)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_sources(sources: tuple[BlindSource, ...]) -> str:
    if not sources:
        return "_Sin fuentes publicadas._"
    sections = []
    for source in sources:
        quote = "\n".join(f"> {line}" for line in source.quote.splitlines())
        sections.append(
            f"- `{source.judgment_id}`, página PDF {source.page}, "
            f"`{source.verification}`\n\n{quote}"
        )
    return "\n\n".join(sections)


def _render_sections(sections: list[str]) -> str:
    rendered = "\n".join(sections)
    return "\n".join(line.rstrip() for line in rendered.splitlines()).rstrip() + "\n"


def render_blind_review_markdown(package: BlindReviewPackage) -> str:
    sections = [
        "# Paquete ciego de revisión F0.3",
        "",
        f"**Rúbrica:** `{package.rubric_version}`.",
        "**Importante:** no abrir la clave de revelado hasta cerrar la revisión.",
        "",
    ]
    for question in package.questions:
        sections.extend(
            [
                f"## {question.question_id}",
                "",
                f"**Intención:** `{question.intent}`.",
                "",
                f"> {question.question}",
                "",
            ]
        )
        for response in question.responses:
            text = response.text or "_Respuesta retirada o sin texto sustantivo._"
            limits = (
                "\n".join(f"- {limit}" for limit in response.limits)
                if response.limits
                else "_Sin límites declarados._"
            )
            sections.extend(
                [
                    f"### Respuesta {response.label}",
                    "",
                    f"**Estado:** `{response.status}`.",
                    "",
                    text,
                    "",
                    "#### Límites",
                    "",
                    limits,
                    "",
                    "#### Fuentes publicadas",
                    "",
                    _render_sources(response.sources),
                    "",
                ]
            )
    return _render_sections(sections)


def render_review_form_markdown(package: BlindReviewPackage) -> str:
    sections = [
        "# Formulario de revisión humana F0.3",
        "",
        "Abrir la [rúbrica](CHAT_STRATEGY_F03_RUBRIC.md) y el "
        "[paquete ciego](CHAT_STRATEGY_F03_BLIND_REVIEW.md).",
        "",
        "Copiar esta plantilla a `CHAT_STRATEGY_F03_REVIEW_COMPLETED.md` antes "
        "de rellenarla. Regenerar F0.3 sobrescribe solo la plantilla.",
        "",
        "No abrir la clave de revelado ni los resultados F0.2 hasta entregar este formulario.",
        "",
        "Puntuaciones (0, 1, 2 o N/A): fidelidad jurídica, relevancia, respaldo "
        "de fuentes, cobertura/contraste, calibración/límites y claridad.",
        "",
    ]
    for question in package.questions:
        sections.extend(
            [
                f"## {question.question_id}",
                "",
                f"> {question.question}",
                "",
            ]
        )
        for response in question.responses:
            sections.extend(
                [
                    f"### Respuesta {response.label}",
                    "",
                    "- G1 — identificadores y páginas válidos: [ ] pasa [ ] falla [ ] N/A",
                    "- G2 — afirmaciones sustantivas respaldadas: [ ] pasa [ ] falla [ ] N/A",
                    "- G3 — distingue hechos, valoración y resultado: [ ] pasa [ ] falla [ ] N/A",
                    "- G4 — no predice el caso del usuario: [ ] pasa [ ] falla [ ] N/A",
                    "- G5 — límites transparentes: [ ] pasa [ ] falla [ ] N/A",
                    "",
                    "| Dimensión | 0/1/2/N/A | Comentario |",
                    "|---|---:|---|",
                    "| Fidelidad jurídica |  |  |",
                    "| Relevancia para la pregunta |  |  |",
                    "| Respaldo de fuentes |  |  |",
                    "| Cobertura y contraste |  |  |",
                    "| Calibración y límites |  |  |",
                    "| Claridad y utilidad |  |  |",
                    "",
                    "**Error crítico:** [ ] no [ ] sí",
                    "",
                    "**Observaciones:**",
                    "",
                ]
            )
        sections.extend(
            [
                "### Preferencia de la pareja",
                "",
                "[ ] X  [ ] Y  [ ] empate  [ ] ninguna",
                "",
                "**Confianza:** [ ] baja  [ ] media  [ ] alta",
                "",
                "**Motivo:**",
                "",
            ]
        )
    return _render_sections(sections)


def generate_blind_review_artifacts(
    *,
    project_root: Path,
    manifest_path: Path,
    package_json_path: Path,
    package_markdown_path: Path,
    review_form_path: Path,
    reveal_key_path: Path,
) -> None:
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("schema_version") != "residenciafiscal-chat-f03-build/1":
        raise ValueError(
            f"schema_version del manifiesto no compatible: {manifest.get('schema_version')!r}"
        )

    rubric_path = _resolve(project_root, manifest["rubric_path"])
    if _sha256(rubric_path) != manifest["rubric_sha256"]:
        raise ValueError("SHA-256 inesperado para la rúbrica")
    dev_set_path = _resolve(project_root, manifest["dev_set_path"])
    if _sha256(dev_set_path) != manifest["dev_set_sha256"]:
        raise ValueError("SHA-256 inesperado para el banco de desarrollo")
    dev_set = json.loads(dev_set_path.read_bytes())
    comparisons: dict[str, ComparisonReport] = {}
    provenance: dict[str, ArtifactProvenance] = {}
    intents: dict[str, str] = {}
    x_strategies: dict[str, StrategyId] = {}
    for item in manifest["items"]:
        artifact_path = _resolve(project_root, item["artifact_path"])
        if _sha256(artifact_path) != item["artifact_sha256"]:
            raise ValueError(
                f"SHA-256 inesperado para {item['question_id']}: {item['artifact_path']}"
            )
        question_id = item["question_id"]
        comparisons[question_id] = ComparisonReport.model_validate_json(artifact_path.read_bytes())
        provenance[question_id] = ArtifactProvenance(
            path=item["artifact_path"],
            sha256=item["artifact_sha256"],
        )
        intents[question_id] = item["intent"]
        x_strategies[question_id] = item["x_strategy"]

    package, key = build_blind_review_package(
        dev_set=dev_set,
        comparisons=comparisons,
        intents=intents,
        x_strategies=x_strategies,
        provenance=provenance,
        rubric_version=manifest["rubric_version"],
        rubric_sha256=manifest["rubric_sha256"],
        dev_set_sha256=manifest["dev_set_sha256"],
    )
    package_json_path.write_text(
        package.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    package_markdown_path.write_text(
        render_blind_review_markdown(package),
        encoding="utf-8",
    )
    review_form_path.write_text(
        render_review_form_markdown(package),
        encoding="utf-8",
    )
    reveal_key_path.write_text(
        key.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--package-json", type=Path, required=True)
    parser.add_argument("--package-markdown", type=Path, required=True)
    parser.add_argument("--review-form", type=Path, required=True)
    parser.add_argument("--reveal-key", type=Path, required=True)
    args = parser.parse_args(argv)
    generate_blind_review_artifacts(
        project_root=args.project_root,
        manifest_path=args.manifest,
        package_json_path=args.package_json,
        package_markdown_path=args.package_markdown,
        review_form_path=args.review_form,
        reveal_key_path=args.reveal_key,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
