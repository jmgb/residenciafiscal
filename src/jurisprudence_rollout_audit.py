"""Segunda pasada automática y determinista sobre casos de riesgo alto."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_catalogs import (
    IssueOutcome,
    IssueType,
    JurisprudenceCaseModel,
    LegalReviewState,
    SpanishResidenceStatus,
)
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_case_models import JurisprudenceCase
from jurisprudence_case_verbatim_validation import validate_case_artifact
from jurisprudence_rollout import load_rollout_manifest
from jurisprudence_rollout_models import RolloutRisk

AuditFocus = Literal[
    "TREATY",
    "PARTIAL_OR_RETROACTION",
    "LOW_ANCHOR_COVERAGE",
    "UNTYPED_RESIDENCE_DETERMINATION",
]
AuditFinding = Literal[
    "TREATY_ANALYSIS_MISSING",
    "RESIDENCE_DETERMINATION_NOT_TYPED",
    "ANCHOR_COVERAGE_LOW",
    "COMPLEX_OUTCOME_REQUIRES_REVIEW",
]


class RolloutAuditCase(JurisprudenceCaseModel):
    judgment_id: str
    audit_status: Literal["NEEDS_HUMAN_REVIEW"]
    focus_flags: tuple[AuditFocus, ...]
    finding_codes: tuple[AuditFinding, ...]
    anchor_count: int
    literal_validation: Literal["PASSED", "FAILED"]
    literal_error: str | None = None


class RolloutAuditReport(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-rollout-audit/1"]
    audit_method: Literal["DETERMINISTIC_INDEPENDENT_PASS"]
    case_count: int
    literal_validation_failures: int
    agent_reviewed_cases: int
    human_approved_cases: int
    finding_counts: dict[AuditFinding, int]
    cases: tuple[RolloutAuditCase, ...]


def _focus_flags(case: JurisprudenceCase) -> tuple[AuditFocus, ...]:
    legal_issues = case.legal_issues
    holdings = case.holdings
    flags: list[AuditFocus] = []
    if case.treaty_analyses or any(
        issue.issue_type == IssueType.TREATY_TIEBREAKER
        or any(criterion.value == "CRIT_CDI_TIEBREAKER" for criterion in issue.criterion_ids)
        for issue in legal_issues
    ):
        flags.append("TREATY")
    if any(
        holding.outcome in {IssueOutcome.PARCIAL, IssueOutcome.RETROACCION} for holding in holdings
    ):
        flags.append("PARTIAL_OR_RETROACTION")
    if len(case.source_anchors) < 5:
        flags.append("LOW_ANCHOR_COVERAGE")
    holdings_by_id = {holding.holding_id: holding for holding in holdings}
    if any(
        (
            (determination := holdings_by_id[issue.holding_id].residence_determination) is None
            or determination.spanish_residence == SpanishResidenceStatus.NOT_DECIDED
        )
        for issue in legal_issues
        if issue.issue_type == IssueType.TAX_RESIDENCE
    ):
        flags.append("UNTYPED_RESIDENCE_DETERMINATION")
    return tuple(flags)


def _findings(case: JurisprudenceCase, flags: tuple[AuditFocus, ...]) -> tuple[AuditFinding, ...]:
    findings: list[AuditFinding] = []
    if "TREATY" in flags and not case.treaty_analyses:
        findings.append("TREATY_ANALYSIS_MISSING")
    if "UNTYPED_RESIDENCE_DETERMINATION" in flags:
        findings.append("RESIDENCE_DETERMINATION_NOT_TYPED")
    if "LOW_ANCHOR_COVERAGE" in flags:
        findings.append("ANCHOR_COVERAGE_LOW")
    if "PARTIAL_OR_RETROACTION" in flags:
        findings.append("COMPLEX_OUTCOME_REQUIRES_REVIEW")
    return tuple(findings)


def audit_high_risk_cases(
    *, manifest_path: Path, output_root: Path, project_root: Path
) -> RolloutAuditReport:
    """Revalida literalidad y marca focos jurídicos sin simular revisión humana."""

    manifest = load_rollout_manifest(manifest_path)
    results: list[RolloutAuditCase] = []
    agent_reviewed = 0
    human_approved = 0
    failures = 0
    for document in manifest.documents:
        if document.risk != RolloutRisk.HIGH:
            continue
        case_path = output_root / f"cases/{document.judgment_id}.case.json"
        verbatim_path = output_root / f"verbatim/{document.judgment_id}.pages.json"
        case = load_jurisprudence_case(case_path.read_bytes())
        agent_reviewed += case.review.legal == LegalReviewState.AGENT_REVIEWED
        human_approved += case.review.legal == LegalReviewState.HUMAN_APPROVED
        literal_status: Literal["PASSED", "FAILED"] = "PASSED"
        literal_error = None
        try:
            validation = validate_case_artifact(
                case_path,
                verbatim_path=verbatim_path,
                project_root=project_root,
            )
            anchor_count = validation.anchor_count
        except (OSError, ValueError) as error:
            failures += 1
            literal_status = "FAILED"
            literal_error = f"{type(error).__name__}: {error}"
            anchor_count = len(case.source_anchors)
        focus_flags = _focus_flags(case)
        results.append(
            RolloutAuditCase(
                judgment_id=document.judgment_id,
                audit_status="NEEDS_HUMAN_REVIEW",
                focus_flags=focus_flags,
                finding_codes=_findings(case, focus_flags),
                anchor_count=anchor_count,
                literal_validation=literal_status,
                literal_error=literal_error,
            )
        )
    finding_counts: dict[AuditFinding, int] = {}
    for result in results:
        for finding in result.finding_codes:
            finding_counts[finding] = finding_counts.get(finding, 0) + 1
    return RolloutAuditReport(
        schema_version="residenciafiscal-rollout-audit/1",
        audit_method="DETERMINISTIC_INDEPENDENT_PASS",
        case_count=len(results),
        literal_validation_failures=failures,
        agent_reviewed_cases=agent_reviewed,
        human_approved_cases=human_approved,
        finding_counts=finding_counts,
        cases=tuple(results),
    )


def render_audit_report(report: RolloutAuditReport) -> str:
    return (
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


def render_audit_markdown(report: RolloutAuditReport) -> str:
    lines = [
        "# Auditoría automática independiente del rollout 106",
        "",
        f"- Casos HIGH: {report.case_count}",
        f"- Fallos de literalidad: {report.literal_validation_failures}",
        f"- Casos revisados por agente: {report.agent_reviewed_cases}",
        f"- Casos aprobados por humano: {report.human_approved_cases}",
        "- Estado: todos siguen pendientes de revisión jurídica humana.",
        "",
        "## Hallazgos que requieren revisión",
        "",
    ]
    lines.extend(
        f"- {finding}: {count}" for finding, count in sorted(report.finding_counts.items())
    )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audita los casos HIGH del rollout.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit_high_risk_cases(
        manifest_path=args.manifest,
        output_root=args.output_root,
        project_root=args.project_root,
    )
    write_case_derivative(render_audit_report(report), args.report)
    write_case_derivative(render_audit_markdown(report), args.markdown)
    print(render_audit_report(report), end="")
    return 0 if report.literal_validation_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
