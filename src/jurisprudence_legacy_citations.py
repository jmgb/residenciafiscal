"""Contrato y gate para cerrar citas heredadas no publicables."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_catalogs import (
    AnchorFidelity,
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
)
from jurisprudence_case_models import JurisprudenceCase


class LegacyCitationDisposition(JurisprudenceCaseModel):
    judgment_id: Identifier
    legacy_citation_id: Identifier
    source_field: NonEmptyText
    disposition: Literal["REPLACED_BY_EXACT_ANCHOR", "RETIRED_AS_PARAPHRASE"]
    replacement_anchor_ids: tuple[Identifier, ...]
    rationale: NonEmptyText

    @model_validator(mode="after")
    def validate_replacements(self) -> LegacyCitationDisposition:
        has_replacements = bool(self.replacement_anchor_ids)
        if has_replacements != (self.disposition == "REPLACED_BY_EXACT_ANCHOR"):
            raise ValueError("la disposición y replacement_anchor_ids no concuerdan")
        return self


class LegacyCitationDispositions(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-legacy-citation-dispositions/1"]
    expected_citations: Annotated[int, Field(gt=0)]
    items: tuple[LegacyCitationDisposition, ...]


@dataclass(frozen=True)
class LegacyCitationValidationResult:
    total: int
    replaced_by_exact_anchor: int
    retired_as_paraphrase: int
    unclassified: int


def load_legacy_citation_dispositions(path: Path) -> LegacyCitationDispositions:
    return LegacyCitationDispositions.model_validate_json(path.read_bytes())


def _legacy_pending(reports_root: Path) -> dict[str, tuple[str, str]]:
    pending = {}
    for path in sorted(reports_root.glob("*.verification.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        judgment_id = path.name.removesuffix(".verification.json")
        for citation in raw["citas"]:
            if not citation["publishable_literal"]:
                pending[citation["id"]] = (
                    judgment_id,
                    citation["source_field"],
                )
    return pending


def validate_legacy_citation_dispositions(
    dispositions: LegacyCitationDispositions,
    *,
    legacy_reports_root: Path,
    cases_root: Path,
) -> LegacyCitationValidationResult:
    """Exige cobertura total y reemplazos que existan en los casos v3."""

    pending = _legacy_pending(legacy_reports_root)
    by_id = {item.legacy_citation_id: item for item in dispositions.items}
    if len(by_id) != len(dispositions.items):
        raise ValueError("items contiene legacy_citation_id duplicado")
    if dispositions.expected_citations != len(dispositions.items):
        raise ValueError("expected_citations no coincide con items")
    if set(by_id) != set(pending):
        missing = sorted(set(pending) - set(by_id))
        extra = sorted(set(by_id) - set(pending))
        raise ValueError(f"cobertura de citas incompleta; missing={missing}, extra={extra}")

    cases: dict[str, JurisprudenceCase] = {}
    for item in dispositions.items:
        expected_judgment, expected_field = pending[item.legacy_citation_id]
        if (item.judgment_id, item.source_field) != (
            expected_judgment,
            expected_field,
        ):
            raise ValueError(f"metadatos heredados no coinciden: {item.legacy_citation_id}")
        case = cases.setdefault(
            item.judgment_id,
            load_jurisprudence_case((cases_root / f"{item.judgment_id}.case.json").read_bytes()),
        )
        anchors_by_id = {anchor.anchor_id: anchor for anchor in case.source_anchors}
        unknown = set(item.replacement_anchor_ids) - anchors_by_id.keys()
        if unknown:
            raise ValueError(
                f"{item.legacy_citation_id} referencia anchors desconocidos: {sorted(unknown)}"
            )
        non_exact = sorted(
            anchor_id
            for anchor_id in item.replacement_anchor_ids
            if anchors_by_id[anchor_id].fidelity != AnchorFidelity.EXACT
        )
        if non_exact:
            raise ValueError(
                f"{item.legacy_citation_id} exige fidelidad EXACT; anchors no exactos: {non_exact}"
            )

    replaced = sum(item.disposition == "REPLACED_BY_EXACT_ANCHOR" for item in dispositions.items)
    retired = len(dispositions.items) - replaced
    return LegacyCitationValidationResult(
        total=len(dispositions.items),
        replaced_by_exact_anchor=replaced,
        retired_as_paraphrase=retired,
        unclassified=len(pending) - len(dispositions.items),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cierra las citas heredadas.")
    parser.add_argument("--dispositions", type=Path, required=True)
    parser.add_argument("--legacy-reports-root", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = validate_legacy_citation_dispositions(
        load_legacy_citation_dispositions(args.dispositions),
        legacy_reports_root=args.legacy_reports_root,
        cases_root=args.cases_root,
    )
    print(
        json.dumps(
            {
                "replaced_by_exact_anchor": result.replaced_by_exact_anchor,
                "retired_as_paraphrase": result.retired_as_paraphrase,
                "total": result.total,
                "unclassified": result.unclassified,
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
