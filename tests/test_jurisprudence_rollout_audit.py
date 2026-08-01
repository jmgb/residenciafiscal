"""Segunda revisión automática independiente del generador de borradores."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "sentencias/jurisprudence_v3_rollout_106.json"
OUTPUT_ROOT = PROJECT_ROOT / "knowledge/jurisprudencia-v3"


def test_audita_los_42_casos_high_sin_conceder_aprobacion_humana() -> None:
    from jurisprudence_rollout_audit import audit_high_risk_cases

    report = audit_high_risk_cases(
        manifest_path=MANIFEST_PATH,
        output_root=OUTPUT_ROOT,
        project_root=PROJECT_ROOT,
    )

    assert report.schema_version == "residenciafiscal-rollout-audit/1"
    assert report.audit_method == "DETERMINISTIC_INDEPENDENT_PASS"
    assert report.case_count == 42
    assert report.literal_validation_failures == 0
    assert report.agent_reviewed_cases == 42
    assert report.human_approved_cases == 0
    assert all(item.audit_status == "NEEDS_HUMAN_REVIEW" for item in report.cases)
    assert {item.judgment_id for item in report.cases} == {
        "san-1071-2025",
        "san-1226-2021",
        "san-1386-2017",
        "san-2132-2025",
        "san-2229-2022",
        "san-3169-2024",
        "san-3306-2025",
        "san-3421-2021",
        "san-3477-2022",
        "san-4187-2023",
        "san-4248-2020",
        "san-4438-2025",
        "san-4670-2019",
        "san-4992-2021",
        "san-5096-2021",
        "san-5630-2023",
        "san-5640-2023",
        "san-6981-2024",
        "san-699-2015",
        "sts-107-2018",
        "sts-109-2018",
        "sts-112-2018",
        "sts-114-2018",
        "sts-115-2018",
        "sts-1608-2023",
        "sts-1682-2022",
        "sts-183-2018",
        "sts-1845-2023",
        "sts-2013-2024",
        "sts-2735-2023",
        "sts-3498-2025",
        "sts-3574-2023",
        "sts-3585-2024",
        "sts-3881-2024",
        "sts-3882-2024",
        "sts-4219-2024",
        "sts-4220-2024",
        "sts-4305-2017",
        "sts-4307-2017",
        "sts-4361-2020",
        "sts-691-2018",
        "sts-695-2018",
    }


def test_auditoria_prioriza_cdi_resultados_complejos_y_anclajes_escasos() -> None:
    from jurisprudence_rollout_audit import audit_high_risk_cases

    report = audit_high_risk_cases(
        manifest_path=MANIFEST_PATH,
        output_root=OUTPUT_ROOT,
        project_root=PROJECT_ROOT,
    )
    flags = {flag for item in report.cases for flag in item.focus_flags}

    assert "TREATY" in flags
    assert "PARTIAL_OR_RETROACTION" in flags
    assert "LOW_ANCHOR_COVERAGE" in flags
    assert "UNTYPED_RESIDENCE_DETERMINATION" in flags
    assert report.finding_counts["TREATY_ANALYSIS_MISSING"] == 13
    assert report.finding_counts["RESIDENCE_DETERMINATION_NOT_TYPED"] == 36
    assert report.finding_counts["ANCHOR_COVERAGE_LOW"] == 6
    assert report.finding_counts["COMPLEX_OUTCOME_REQUIRES_REVIEW"] == 5
