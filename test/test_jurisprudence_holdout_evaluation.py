"""Banco holdout congelado y medición sin ajuste posterior."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval/corpus.json"
BANK_PATH = PROJECT_ROOT / "docs/experiments/CHAT_QUESTION_HOLDOUT_E.json"
LOCK_PATH = PROJECT_ROOT / "docs/experiments/CHAT_QUESTION_HOLDOUT_E.lock.json"


def test_carga_el_holdout_solo_si_coincide_con_su_lock() -> None:
    from jurisprudence_holdout_evaluation import load_frozen_holdout

    frozen = load_frozen_holdout(
        lock_path=LOCK_PATH,
        project_root=PROJECT_ROOT,
    )

    assert frozen.lock.policy == "NEVER_TUNE_PHASE_D_WITH_THIS_BANK"
    assert frozen.lock.question_count == 20
    assert len(frozen.bank.questions) == 20
    assert all(item.question_id.startswith("HE-") for item in frozen.bank.questions)


def test_rechaza_un_holdout_modificado_despues_del_lock(tmp_path: Path) -> None:
    from jurisprudence_holdout_evaluation import load_frozen_holdout

    bank = tmp_path / "bank.json"
    bank.write_bytes(BANK_PATH.read_bytes() + b"\n")
    lock = tmp_path / "lock.json"
    lock.write_text(
        LOCK_PATH.read_text(encoding="utf-8").replace(
            "docs/experiments/CHAT_QUESTION_HOLDOUT_E.json",
            "bank.json",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="bank_sha256"):
        load_frozen_holdout(lock_path=lock, project_root=tmp_path)


def test_exporta_la_primera_medicion_sin_convertirla_en_gate(
    tmp_path: Path,
) -> None:
    from jurisprudence_holdout_evaluation import export_holdout_evaluation

    output = tmp_path / "holdout-evaluation.json"
    result = export_holdout_evaluation(
        corpus_path=CORPUS_PATH,
        lock_path=LOCK_PATH,
        output_path=output,
        project_root=PROJECT_ROOT,
    )

    assert result.report.evaluation_policy == "OBSERVE_ONLY_NO_TUNING"
    assert result.report.question_count == 20
    assert result.report.status == "RECORDED"
    assert result.report.behavior_accuracy <= 1
    assert result.report.zero_source_safety <= 1
    assert output.is_file()


def test_cli_exporta_el_holdout_con_rutas_explicitas(tmp_path: Path) -> None:
    from jurisprudence_holdout_evaluation import main

    output = tmp_path / "holdout.json"

    assert (
        main(
            [
                "--corpus",
                str(CORPUS_PATH),
                "--lock",
                str(LOCK_PATH),
                "--output",
                str(output),
                "--project-root",
                str(PROJECT_ROOT),
            ]
        )
        == 0
    )
    assert output.is_file()
