"""Planificación reanudable de fase E sin enumerar el corpus real."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from okf_provenance import sha256_file


def _manifest_payload() -> dict[str, Any]:
    documents = []
    for index, batch_id in ((1, "batch-001"), (2, "batch-001"), (3, "batch-002")):
        judgment_id = f"san-{index}-2026"
        documents.append(
            {
                "judgment_id": judgment_id,
                "source_file": f"sentencias/SAN_{index}_2026.pdf",
                "source_sha256": str(index) * 64,
                "proposal_path": f"knowledge/proposals/{judgment_id}.json",
                "evaluation_path": f"knowledge/evaluations/{judgment_id}.json",
                "batch_id": batch_id,
                "risk": "HIGH" if index == 1 else "STANDARD",
            }
        )
    return {
        "schema_version": "residenciafiscal-rollout/1",
        "rollout_id": "jurisprudencia-v3-fase-e",
        "expected_documents": 3,
        "documents": documents,
    }


def _write_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "rollout.json"
    path.write_text(json.dumps(_manifest_payload()), encoding="utf-8")
    return path


def _build_result(
    judgment_id: str,
    *,
    legal_review: str = "AGENT_REVIEWED",
):
    from jurisprudence_rollout_models import RolloutBuildResult

    return RolloutBuildResult(
        judgment_id=judgment_id,
        case_sha256="a" * 64,
        retrieval_sha256="b" * 64,
        markdown_sha256="c" * 64,
        verbatim_sha256="d" * 64,
        legal_review=legal_review,
    )


def test_manifiesto_rechaza_cardinalidad_y_documentos_duplicados() -> None:
    from jurisprudence_rollout_models import RolloutManifest

    raw = _manifest_payload()
    raw["expected_documents"] = 4
    with pytest.raises(ValidationError, match="expected_documents"):
        RolloutManifest.model_validate(raw)

    raw = _manifest_payload()
    raw["documents"][1]["judgment_id"] = raw["documents"][0]["judgment_id"]
    with pytest.raises(ValidationError, match="duplicado"):
        RolloutManifest.model_validate(raw)

    raw = _manifest_payload()
    raw["documents"][1]["source_file"] = raw["documents"][0]["source_file"]
    with pytest.raises(ValidationError, match="source_file duplicado"):
        RolloutManifest.model_validate(raw)


def test_inicializa_un_estado_determinista_por_lotes(tmp_path: Path) -> None:
    from jurisprudence_rollout import initialize_rollout

    manifest_path = _write_manifest(tmp_path)
    first = initialize_rollout(manifest_path)
    second = initialize_rollout(manifest_path)

    assert first == second
    assert tuple(item.batch_id for item in first.documents) == (
        "batch-001",
        "batch-001",
        "batch-002",
    )
    assert all(item.execution_status == "PENDING" for item in first.documents)
    assert all(item.attempts == 0 for item in first.documents)


def test_reanuda_el_lote_fallido_sin_repetir_documentos_superados(
    tmp_path: Path,
) -> None:
    from jurisprudence_rollout import execute_next_batch, load_rollout_state

    manifest_path = _write_manifest(tmp_path)
    state_path = tmp_path / "state.json"
    attempts: dict[str, int] = {}

    def executor(document):
        attempts[document.judgment_id] = attempts.get(document.judgment_id, 0) + 1
        if document.judgment_id == "san-2-2026" and attempts[document.judgment_id] == 1:
            raise RuntimeError("fallo controlado")
        return _build_result(document.judgment_id)

    first = execute_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        executor=executor,
    )
    assert first.batch_id == "batch-001"
    assert first.passed == ("san-1-2026",)
    assert first.failed == ("san-2-2026",)

    with pytest.raises(ValueError, match="retry_failed"):
        execute_next_batch(
            manifest_path=manifest_path,
            state_path=state_path,
            executor=executor,
        )

    resumed = execute_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        executor=executor,
        retry_failed=True,
    )
    assert resumed.passed == ("san-2-2026",)
    assert attempts == {"san-1-2026": 1, "san-2-2026": 2}

    state = load_rollout_state(state_path)
    by_id = {item.judgment_id: item for item in state.documents}
    assert by_id["san-1-2026"].attempts == 1
    assert by_id["san-2-2026"].attempts == 2
    assert by_id["san-3-2026"].execution_status == "PENDING"


def test_rechaza_estado_que_no_corresponde_exactamente_al_manifiesto(
    tmp_path: Path,
) -> None:
    from jurisprudence_rollout import (
        execute_next_batch,
        initialize_rollout,
        write_rollout_state,
    )

    manifest_path = _write_manifest(tmp_path)
    state_path = tmp_path / "state.json"
    state = initialize_rollout(manifest_path)
    write_rollout_state(
        state.model_copy(update={"documents": state.documents[:-1]}),
        state_path,
    )

    with pytest.raises(ValueError, match="documentos del estado"):
        execute_next_batch(
            manifest_path=manifest_path,
            state_path=state_path,
            executor=lambda document: _build_result(document.judgment_id),
        )


def test_resultado_de_build_debe_pertenecer_al_documento_en_ejecucion(
    tmp_path: Path,
) -> None:
    from jurisprudence_rollout import execute_next_batch, load_rollout_state

    manifest_path = _write_manifest(tmp_path)
    state_path = tmp_path / "state.json"

    result = execute_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        executor=lambda _document: _build_result("san-ajena-2026"),
    )

    assert result.failed == ("san-1-2026", "san-2-2026")
    state = load_rollout_state(state_path)
    assert all(
        "judgment_id no coincide" in (document.last_error or "") for document in state.documents[:2]
    )


def test_gate_separa_build_tecnico_de_aprobacion_humana(tmp_path: Path) -> None:
    from jurisprudence_rollout import batch_gate, execute_next_batch

    manifest_path = _write_manifest(tmp_path)
    state_path = tmp_path / "agent-reviewed-state.json"
    execute_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        executor=lambda document: _build_result(document.judgment_id),
    )

    assert batch_gate(state_path, "batch-001") == "AWAITING_HUMAN_REVIEW"

    approved_state = tmp_path / "human-approved-state.json"
    execute_next_batch(
        manifest_path=manifest_path,
        state_path=approved_state,
        executor=lambda document: _build_result(
            document.judgment_id,
            legal_review="HUMAN_APPROVED",
        ),
    )
    assert batch_gate(approved_state, "batch-001") == "PASSED"


def test_adaptador_ejecuta_el_pipeline_real_para_un_documento(
    tmp_path: Path,
) -> None:
    from test_export_jurisprudence_sample import _copy_pilot_project

    from jurisprudence_rollout import batch_gate, load_rollout_state
    from jurisprudence_rollout_pipeline import execute_rollout_next_batch

    project_root = _copy_pilot_project(tmp_path)
    manifest_path = project_root / "sentencias/rollout.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-rollout/1",
                "rollout_id": "rollout-prueba",
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
                        "batch_id": "batch-001",
                        "risk": "HIGH",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    state_path = project_root / "build/rollout-state.json"
    output_root = project_root / "build/corpus"

    result = execute_rollout_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        output_root=output_root,
        project_root=project_root,
    )

    assert result.passed == ("san-1210-2023",)
    state = load_rollout_state(state_path)
    assert state.documents[0].execution_status == "BUILD_PASSED"
    assert state.documents[0].case_sha256 == sha256_file(
        output_root / "cases/san-1210-2023.case.json"
    )
    assert batch_gate(state_path, "batch-001") == "AWAITING_HUMAN_REVIEW"


def test_cli_inicializa_y_muestra_estado_sin_ejecutar_documentos(
    tmp_path: Path,
) -> None:
    from jurisprudence_rollout_cli import main

    manifest_path = _write_manifest(tmp_path)
    state_path = tmp_path / "state.json"

    assert (
        main(
            [
                "init",
                "--manifest",
                str(manifest_path),
                "--state",
                str(state_path),
            ]
        )
        == 0
    )
    assert main(["status", "--state", str(state_path)]) == 0
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["documents"][0]["execution_status"] == "PENDING"


def test_rollout_rechaza_una_cuestion_residencial_nueva_sin_faceta_tipadada(
    tmp_path: Path,
) -> None:
    from test_export_jurisprudence_sample import _copy_pilot_project

    from jurisprudence_rollout import load_rollout_state
    from jurisprudence_rollout_pipeline import execute_rollout_next_batch

    project_root = _copy_pilot_project(tmp_path)
    proposal_path = (
        project_root / "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json"
    )
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["holdings"][0].pop("residence_determination")
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    manifest_path = project_root / "rollout.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-rollout/1",
                "rollout_id": "rollout-sin-faceta",
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
                        "batch_id": "batch-001",
                        "risk": "HIGH",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    state_path = project_root / "state.json"

    result = execute_rollout_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        output_root=project_root / "build",
        project_root=project_root,
    )

    assert result.failed == ("san-1210-2023",)
    state = load_rollout_state(state_path)
    assert "residence_determination" in (state.documents[0].last_error or "")
