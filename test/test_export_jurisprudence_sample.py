"""Orquestación real y reentrante del pipeline v3 por manifiesto."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from okf_provenance import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _copy_pilot_project(tmp_path: Path) -> Path:
    files = (
        "sentencias/SAN_1210_2023.pdf",
        "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json",
        "knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json",
        "knowledge/jurisprudencia-muestra-5/sources/san-1210-2023.analysis.json",
        "knowledge/annotations/san-1210-2023.yaml",
    )
    for relative in files:
        source = PROJECT_ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tmp_path


def _write_manifest(project_root: Path) -> Path:
    manifest_path = project_root / "sentencias/jurisprudence_v3_sample.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-jurisprudence-sample/1",
                "sample_id": "piloto-v3",
                "expected_documents": 1,
                "documents": [
                    {
                        "judgment_id": "san-1210-2023",
                        "source_file": "sentencias/SAN_1210_2023.pdf",
                        "source_sha256": sha256_file(project_root / "sentencias/SAN_1210_2023.pdf"),
                        "proposal_path": (
                            "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json"
                        ),
                        "evaluation_path": (
                            "knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json"
                        ),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def test_exporta_el_ciclo_completo_y_es_reentrante(tmp_path: Path) -> None:
    from export_jurisprudence_sample import export_jurisprudence_sample

    project_root = _copy_pilot_project(tmp_path)
    manifest_path = _write_manifest(project_root)
    output_root = project_root / "knowledge/jurisprudencia-v3"

    first = export_jurisprudence_sample(
        manifest_path=manifest_path,
        output_root=output_root,
        project_root=project_root,
    )
    expected_paths = (
        output_root / "verbatim/san-1210-2023.pages.json",
        output_root / "cases/san-1210-2023.case.json",
        output_root / "perfiles/san-1210-2023.md",
        output_root / "retrieval/san-1210-2023.issues.json",
        output_root / "reports/san-1210-2023.case-validation.json",
        output_root / "reports/san-1210-2023.derivatives-validation.json",
        output_root / "sample-build.json",
    )
    first_hashes = tuple(sha256_file(path) for path in expected_paths)

    second = export_jurisprudence_sample(
        manifest_path=manifest_path,
        output_root=output_root,
        project_root=project_root,
    )

    assert first.document_ids == ("san-1210-2023",)
    assert second.document_ids == first.document_ids
    assert tuple(sha256_file(path) for path in expected_paths) == first_hashes
    report = json.loads((output_root / "sample-build.json").read_text(encoding="utf-8"))
    assert report["validation"] == "passed"
    assert report["documents"][0]["legal_issue_count"] == 3


def test_permite_reconstruir_solo_un_subconjunto(tmp_path: Path) -> None:
    from export_jurisprudence_sample import export_jurisprudence_sample

    project_root = _copy_pilot_project(tmp_path)
    manifest_path = _write_manifest(project_root)

    result = export_jurisprudence_sample(
        manifest_path=manifest_path,
        output_root=project_root / "builds/muestra-v3",
        project_root=project_root,
        only_judgment_ids=("san-1210-2023",),
    )

    assert result.document_ids == ("san-1210-2023",)

    try:
        export_jurisprudence_sample(
            manifest_path=manifest_path,
            output_root=project_root / "builds/muestra-v3",
            project_root=project_root,
            only_judgment_ids=("san-inexistente",),
        )
    except ValueError as exc:
        assert "san-inexistente" in str(exc)
    else:
        raise AssertionError("debe rechazar un judgment_id ausente del manifiesto")
