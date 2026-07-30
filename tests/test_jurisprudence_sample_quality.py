"""Métricas de calidad y coste de revisión de la muestra v3."""

from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = PROJECT_ROOT / "knowledge/jurisprudencia-v3/cases"
MANIFEST_PATH = PROJECT_ROOT / "sentencias/jurisprudence_v3_sample_5.json"


def test_mide_calidad_sin_confundir_nulos_con_campos_invalidos() -> None:
    from jurisprudence_sample_quality import build_sample_quality_report

    report = build_sample_quality_report(
        tuple(sorted(CASES_ROOT.glob("san-*.case.json"))),
        sample_id="jurisprudencia-v3-piloto-5",
        project_root=PROJECT_ROOT,
    )

    assert report.case_count == 5
    assert report.required_field_failures == 0
    assert report.noncanonical_catalog_values == 0
    assert report.exact_anchor_count >= 60
    assert report.items_requiring_human_review > 0
    assert report.human_approved_items == 0
    assert report.null_field_occurrences["prompt_sha256"] == 5
    assert report.by_case[0].case_resource.startswith("knowledge/jurisprudencia-v3/cases/")


def test_selecciona_solo_los_casos_del_manifiesto_y_omite_stale(
    tmp_path: Path,
) -> None:
    from jurisprudence_sample_quality import case_paths_from_manifest

    cases_root = tmp_path / "cases"
    shutil.copytree(CASES_ROOT, cases_root)
    shutil.copyfile(
        CASES_ROOT / "san-1071-2025.case.json",
        cases_root / "san-9999-2099.case.json",
    )

    paths = case_paths_from_manifest(
        MANIFEST_PATH,
        cases_root=cases_root,
    )

    assert len(paths) == 5
    assert all(path.name != "san-9999-2099.case.json" for path in paths)
