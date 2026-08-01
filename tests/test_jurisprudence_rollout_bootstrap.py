"""Preparación reproducible de todos los insumos de fase E."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from okf_provenance import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# El bootstrap parte del JSONL del analizador retirado, que vive en `output/` y
# no se versiona: en un clon limpio —y en CI— estos casos se saltan en vez de
# fallar. Donde el artefacto está, se ejecutan enteros.
LEGACY_ANALYSIS = PROJECT_ROOT / "output/analisis_02012026_155032.jsonl"

pytestmark = pytest.mark.skipif(
    not LEGACY_ANALYSIS.exists(),
    reason=(
        f"falta {LEGACY_ANALYSIS.relative_to(PROJECT_ROOT)}, el artefacto histórico del "
        "analizador retirado; `output/` no se versiona"
    ),
)


def _legacy_record(source_file: str) -> dict[str, object]:
    with LEGACY_ANALYSIS.open(encoding="utf-8") as stream:
        return next(
            record for line in stream if (record := json.loads(line))["archivo"] == source_file
        )


def test_prepara_verbatim_propuesta_evaluacion_y_manifiesto(tmp_path: Path) -> None:
    from jurisprudence_rollout_bootstrap import bootstrap_rollout_inputs

    source_file = "SAN_1210_2023.pdf"
    pdf = tmp_path / "sentencias" / source_file
    pdf.parent.mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "sentencias" / source_file, pdf)
    legacy = tmp_path / "output/analisis.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(_legacy_record(source_file)) + "\n", encoding="utf-8")
    manifest_path = tmp_path / "sentencias/jurisprudence_v3_rollout.json"

    result = bootstrap_rollout_inputs(
        legacy_path=legacy,
        manifest_path=manifest_path,
        output_root=tmp_path / "knowledge/jurisprudencia-v3",
        project_root=tmp_path,
        generated_at=datetime(2026, 8, 1, tzinfo=UTC),
        batch_size=10,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    document = manifest["documents"][0]
    assert result.generated_documents == ("san-1210-2023",)
    assert manifest["expected_documents"] == 1
    assert document["source_sha256"] == sha256_file(pdf)
    assert document["proposal_sha256"] == sha256_file(tmp_path / document["proposal_path"])
    assert document["evaluation_sha256"] == sha256_file(tmp_path / document["evaluation_path"])
    assert document["batch_id"] == "batch-001"
    assert (tmp_path / document["proposal_path"]).is_file()
    assert (tmp_path / document["evaluation_path"]).is_file()
    assert (tmp_path / "knowledge/jurisprudencia-v3/verbatim/san-1210-2023.pages.json").is_file()


def test_no_sobrescribe_las_propuestas_curadas_existentes(tmp_path: Path) -> None:
    from jurisprudence_rollout_bootstrap import bootstrap_rollout_inputs

    source_file = "SAN_1210_2023.pdf"
    pdf = tmp_path / "sentencias" / source_file
    pdf.parent.mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "sentencias" / source_file, pdf)
    legacy = tmp_path / "output/analisis.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(_legacy_record(source_file)) + "\n", encoding="utf-8")
    proposal = tmp_path / "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json"
    evaluation = tmp_path / "knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json"
    proposal.parent.mkdir(parents=True)
    evaluation.parent.mkdir(parents=True)
    proposal.write_text('{"curated": true}\n', encoding="utf-8")
    evaluation.write_text('{"curated": true}\n', encoding="utf-8")

    result = bootstrap_rollout_inputs(
        legacy_path=legacy,
        manifest_path=tmp_path / "sentencias/rollout.json",
        output_root=tmp_path / "knowledge/jurisprudencia-v3",
        project_root=tmp_path,
        generated_at=datetime(2026, 8, 1, tzinfo=UTC),
        batch_size=10,
    )

    assert result.preserved_documents == ("san-1210-2023",)
    assert json.loads(proposal.read_text(encoding="utf-8")) == {"curated": True}
    assert json.loads(evaluation.read_text(encoding="utf-8")) == {"curated": True}


def test_cli_expone_el_bootstrap_reproducible(tmp_path: Path) -> None:
    from jurisprudence_rollout_bootstrap import main

    source_file = "SAN_1210_2023.pdf"
    pdf = tmp_path / "sentencias" / source_file
    pdf.parent.mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "sentencias" / source_file, pdf)
    legacy = tmp_path / "output/analisis.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(_legacy_record(source_file)) + "\n", encoding="utf-8")
    manifest = tmp_path / "sentencias/rollout.json"

    assert (
        main(
            [
                "--legacy",
                str(legacy),
                "--manifest",
                str(manifest),
                "--output-root",
                str(tmp_path / "knowledge/jurisprudencia-v3"),
                "--project-root",
                str(tmp_path),
                "--generated-at",
                "2026-08-01T00:00:00+00:00",
            ]
        )
        == 0
    )
    assert manifest.is_file()


def test_regenera_un_borrador_creado_por_el_mismo_bootstrap(tmp_path: Path) -> None:
    from jurisprudence_rollout_bootstrap import bootstrap_rollout_inputs

    source_file = "SAN_1210_2023.pdf"
    pdf = tmp_path / "sentencias" / source_file
    pdf.parent.mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "sentencias" / source_file, pdf)
    legacy = tmp_path / "output/analisis.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(_legacy_record(source_file)) + "\n", encoding="utf-8")
    proposal = tmp_path / "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json"
    evaluation = tmp_path / "knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json"
    proposal.parent.mkdir(parents=True)
    evaluation.parent.mkdir(parents=True)
    proposal.write_text(
        json.dumps(
            {"judgment": {"analysis_provenance": {"producer": "residenciafiscal-legacy-bootstrap"}}}
        ),
        encoding="utf-8",
    )
    evaluation.write_text('{"stale": true}\n', encoding="utf-8")

    result = bootstrap_rollout_inputs(
        legacy_path=legacy,
        manifest_path=tmp_path / "sentencias/rollout.json",
        output_root=tmp_path / "knowledge/jurisprudencia-v3",
        project_root=tmp_path,
        generated_at=datetime(2026, 8, 1, tzinfo=UTC),
        batch_size=10,
    )

    assert result.generated_documents == ("san-1210-2023",)
    assert json.loads(evaluation.read_text(encoding="utf-8"))["schema_version"] == (
        "residenciafiscal-case-question-evaluation/1"
    )
