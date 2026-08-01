"""Evaluación técnica separada para el corpus ampliado."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_construye_un_banco_por_sentencia_sin_incluir_fuera_de_alcance(
    tmp_path: Path,
) -> None:
    from jurisprudence_rollout_evaluation import build_rollout_evaluation_bank

    manifest = tmp_path / "sentencias/rollout.json"
    manifest.parent.mkdir(parents=True)
    evaluation_root = tmp_path / "knowledge/jurisprudencia-v3/evaluations"
    retrieval_root = tmp_path / "knowledge/jurisprudencia-v3/retrieval"
    evaluation_root.mkdir(parents=True)
    retrieval_root.mkdir(parents=True)
    source_evaluation = (
        PROJECT_ROOT / "knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json"
    )
    source_index = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval/san-1210-2023.issues.json"
    shutil.copyfile(source_evaluation, evaluation_root / source_evaluation.name)
    shutil.copyfile(source_index, retrieval_root / source_index.name)
    out_evaluation = json.loads(source_evaluation.read_text(encoding="utf-8"))
    out_evaluation["judgment_id"] = "san-fuera-2026"
    (evaluation_root / "san-fuera-2026.questions.json").write_text(
        json.dumps(out_evaluation), encoding="utf-8"
    )
    out_index = json.loads(source_index.read_text(encoding="utf-8"))
    out_index["judgment"]["judgment_id"] = "san-fuera-2026"
    out_index["judgment"]["is_tax_residence_case"] = False
    for unit in out_index["units"]:
        unit["judgment_id"] = "san-fuera-2026"
        unit["unit_id"] = f"san-fuera-2026-{unit['issue']['issue_id']}"
    (retrieval_root / "san-fuera-2026.issues.json").write_text(
        json.dumps(out_index), encoding="utf-8"
    )
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-rollout/1",
                "rollout_id": "rollout-evaluation",
                "expected_documents": 2,
                "documents": [
                    {
                        "judgment_id": judgment_id,
                        "source_file": f"sentencias/{judgment_id}.pdf",
                        "source_sha256": character * 64,
                        "proposal_path": f"knowledge/{judgment_id}.proposal.json",
                        "evaluation_path": (
                            f"knowledge/jurisprudencia-v3/evaluations/{judgment_id}.questions.json"
                        ),
                        "batch_id": "batch-001",
                        "risk": "STANDARD",
                    }
                    for judgment_id, character in (
                        ("san-1210-2023", "a"),
                        ("san-fuera-2026", "b"),
                    )
                ],
            }
        ),
        encoding="utf-8",
    )

    bank = build_rollout_evaluation_bank(
        manifest_path=manifest,
        output_root=tmp_path / "knowledge/jurisprudencia-v3",
        project_root=tmp_path,
    )

    assert len(bank.questions) == len(out_evaluation["questions"])
    assert all(item.question_id.startswith("san-1210-2023-") for item in bank.questions)
    assert all(item.expected_judgment_ids == ("san-1210-2023",) for item in bank.questions)


def test_exporta_metricas_de_recuperacion_del_rollout(tmp_path: Path) -> None:
    from jurisprudence_rollout_evaluation import export_rollout_evaluation

    manifest = PROJECT_ROOT / "sentencias/jurisprudence_v3_rollout_106.json"
    result = export_rollout_evaluation(
        manifest_path=manifest,
        output_root=PROJECT_ROOT / "knowledge/jurisprudencia-v3",
        bank_path=tmp_path / "bank.json",
        report_path=tmp_path / "report.json",
        project_root=PROJECT_ROOT,
    )

    assert result.question_count >= 67
    assert 0 <= result.expected_recall_at_5 <= 1
    assert 0 <= result.expected_recall_at_12 <= 1
    assert (tmp_path / "bank.json").is_file()
    assert (tmp_path / "report.json").is_file()

    from jurisprudence_rollout_evaluation import main

    assert (
        main(
            [
                "--manifest",
                str(manifest),
                "--output-root",
                str(PROJECT_ROOT / "knowledge/jurisprudencia-v3"),
                "--bank",
                str(tmp_path / "bank-cli.json"),
                "--report",
                str(tmp_path / "report-cli.json"),
                "--project-root",
                str(PROJECT_ROOT),
            ]
        )
        == 0
    )
