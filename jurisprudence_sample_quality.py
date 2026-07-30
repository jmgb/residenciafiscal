"""Métricas reproducibles de calidad y cola de revisión de la muestra v3."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Literal

from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_catalogs import Identifier, JurisprudenceCaseModel, Sha256
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_sample_manifest import load_sample_manifest
from okf_provenance import sha256_file


class CaseQualitySummary(JurisprudenceCaseModel):
    judgment_id: Identifier
    case_resource: str
    case_sha256: Sha256
    entity_count: int
    source_anchor_count: int
    review_item_count: int
    items_requiring_human_review: int


class SampleQualityReport(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-sample-quality/1"]
    sample_id: Identifier
    case_count: int
    required_field_failures: int
    noncanonical_catalog_values: int
    exact_anchor_count: int
    exact_with_ellipsis_anchor_count: int
    source_fragment_count: int
    review_item_count: int
    agent_reviewed_items: int
    human_approved_items: int
    items_requiring_human_review: int
    null_field_occurrences: dict[str, int]
    by_case: tuple[CaseQualitySummary, ...]


def _objects(value: object) -> Iterator[dict[str, object]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _objects(nested)


def _relative(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    root = project_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"caso fuera de project_root: {path}")
    return resolved.relative_to(root).as_posix()


def _reviews(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    return tuple(item for item in _objects(payload) if {"technical", "legal"} <= set(item))


def _entity_count(payload: dict[str, object]) -> int:
    collections = (
        "legal_issues",
        "facts",
        "evidence_findings",
        "legal_rules",
        "holdings",
        "burden_of_proof_steps",
        "presence_events",
        "presence_periods",
        "treaty_analyses",
        "source_anchors",
    )
    count = 0
    for name in collections:
        value = payload[name]
        if not isinstance(value, list):
            raise ValueError(f"{name} no es una colección")
        count += len(value)
    return count


def build_sample_quality_report(
    case_paths: tuple[Path, ...],
    *,
    sample_id: str,
    project_root: Path,
) -> SampleQualityReport:
    """Mide campos inciertos y revisión sin reinterpretar el contenido jurídico."""

    summaries = []
    nulls: Counter[str] = Counter()
    exact = ellipsis = fragments = 0
    all_reviews: list[dict[str, object]] = []
    for path in case_paths:
        case = load_jurisprudence_case(path.read_bytes())
        payload = case.model_dump(mode="json")
        reviews = _reviews(payload)
        all_reviews.extend(reviews)
        for item in _objects(payload):
            nulls.update(key for key, value in item.items() if value is None)
        exact += sum(anchor.fidelity == "EXACT" for anchor in case.source_anchors)
        ellipsis += sum(anchor.fidelity == "EXACT_WITH_ELLIPSIS" for anchor in case.source_anchors)
        fragments += sum(len(anchor.fragments) for anchor in case.source_anchors)
        summaries.append(
            CaseQualitySummary(
                judgment_id=case.judgment.judgment_id,
                case_resource=_relative(path, project_root),
                case_sha256=sha256_file(path),
                entity_count=_entity_count(payload),
                source_anchor_count=len(case.source_anchors),
                review_item_count=len(reviews),
                items_requiring_human_review=sum(
                    item["legal"] != "HUMAN_APPROVED" for item in reviews
                ),
            )
        )
    agent_reviewed = sum(item["legal"] == "AGENT_REVIEWED" for item in all_reviews)
    human_approved = sum(item["legal"] == "HUMAN_APPROVED" for item in all_reviews)
    return SampleQualityReport(
        schema_version="residenciafiscal-sample-quality/1",
        sample_id=sample_id,
        case_count=len(case_paths),
        required_field_failures=0,
        noncanonical_catalog_values=0,
        exact_anchor_count=exact,
        exact_with_ellipsis_anchor_count=ellipsis,
        source_fragment_count=fragments,
        review_item_count=len(all_reviews),
        agent_reviewed_items=agent_reviewed,
        human_approved_items=human_approved,
        items_requiring_human_review=len(all_reviews) - human_approved,
        null_field_occurrences=dict(sorted(nulls.items())),
        by_case=tuple(summaries),
    )


def render_sample_quality_report(report: SampleQualityReport) -> str:
    return (
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def case_paths_from_manifest(
    manifest_path: Path,
    *,
    cases_root: Path,
) -> tuple[Path, ...]:
    """Selecciona exactamente los casos declarados, ignorando restos del directorio."""

    manifest = load_sample_manifest(manifest_path)
    paths = tuple(
        cases_root / f"{document.judgment_id}.case.json" for document in manifest.documents
    )
    missing = tuple(path for path in paths if not path.is_file())
    if missing:
        raise ValueError(f"faltan casos del manifiesto: {[path.name for path in missing]}")
    return paths


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mide calidad de casos v3.")
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = load_sample_manifest(args.manifest)
    report = build_sample_quality_report(
        case_paths_from_manifest(args.manifest, cases_root=args.cases_root),
        sample_id=manifest.sample_id,
        project_root=args.project_root,
    )
    write_case_derivative(render_sample_quality_report(report), args.output)
    print(
        json.dumps(
            {
                "cases": report.case_count,
                "human_review_queue": report.items_requiring_human_review,
                "output": str(args.output),
                "validation": "passed",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
