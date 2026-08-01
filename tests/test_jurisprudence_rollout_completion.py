"""Cierre técnico de fase E sin falsificar el gate jurídico humano."""

from __future__ import annotations

import json
from pathlib import Path

from okf_provenance import sha256_file


def test_cierra_corpus_agregado_como_agent_reviewed(tmp_path: Path) -> None:
    from test_export_jurisprudence_sample import _copy_pilot_project

    from jurisprudence_rollout import load_rollout_state
    from jurisprudence_rollout_completion import finalize_rollout
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
    state_path = project_root / "output/rollout-state.json"
    output_root = project_root / "knowledge/jurisprudencia-v3"
    execute_rollout_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        output_root=output_root,
        project_root=project_root,
    )
    pilot_corpus = output_root / "retrieval/corpus.json"
    pilot_corpus.write_text("corpus piloto intacto\n", encoding="utf-8")

    result = finalize_rollout(
        manifest_path=manifest_path,
        state_path=state_path,
        output_root=output_root,
        project_root=project_root,
    )

    assert load_rollout_state(state_path).documents[0].legal_review == "AGENT_REVIEWED"
    assert result.document_count == 1
    assert result.retrieval_document_count == 1
    assert result.publication_status == "AGENT_REVIEWED_ONLY"
    assert pilot_corpus.read_text(encoding="utf-8") == "corpus piloto intacto\n"
    assert (output_root / "retrieval/rollout-1.corpus.json").is_file()
    assert (output_root / "reports/rollout-1.quality.json").is_file()
    build = json.loads((output_root / "rollout-build.json").read_text(encoding="utf-8"))
    assert build["human_approved_documents"] == 0
    assert build["publication_status"] == "AGENT_REVIEWED_ONLY"

    from jurisprudence_rollout_completion import main

    assert (
        main(
            [
                "--manifest",
                str(manifest_path),
                "--state",
                str(state_path),
                "--output-root",
                str(output_root),
                "--project-root",
                str(project_root),
            ]
        )
        == 0
    )


def test_rechaza_el_cierre_si_queda_un_documento_sin_compilar(tmp_path: Path) -> None:
    from jurisprudence_rollout import initialize_rollout, write_rollout_state
    from jurisprudence_rollout_completion import finalize_rollout

    manifest_path = tmp_path / "rollout.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-rollout/1",
                "rollout_id": "rollout-pendiente",
                "expected_documents": 1,
                "documents": [
                    {
                        "judgment_id": "san-1-2026",
                        "source_file": "sentencias/SAN_1_2026.pdf",
                        "source_sha256": "a" * 64,
                        "proposal_path": "knowledge/proposal.json",
                        "evaluation_path": "knowledge/evaluation.json",
                        "batch_id": "batch-001",
                        "risk": "STANDARD",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    state_path = tmp_path / "state.json"
    write_rollout_state(initialize_rollout(manifest_path), state_path)

    try:
        finalize_rollout(
            manifest_path=manifest_path,
            state_path=state_path,
            output_root=tmp_path / "knowledge",
            project_root=tmp_path,
        )
    except ValueError as error:
        assert "BUILD_PASSED" in str(error)
    else:
        raise AssertionError("no debe cerrar un rollout incompleto")


def test_rechaza_el_cierre_si_un_derivado_cambio_despues_del_build(tmp_path: Path) -> None:
    from test_export_jurisprudence_sample import _copy_pilot_project

    from jurisprudence_rollout_completion import finalize_rollout
    from jurisprudence_rollout_pipeline import execute_rollout_next_batch

    project_root = _copy_pilot_project(tmp_path)
    manifest_path = project_root / "sentencias/rollout.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-rollout/1",
                "rollout_id": "rollout-derivado-congelado",
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
    output_root = project_root / "knowledge/jurisprudencia-v3"
    execute_rollout_next_batch(
        manifest_path=manifest_path,
        state_path=state_path,
        output_root=output_root,
        project_root=project_root,
    )
    retrieval = output_root / "retrieval/san-1210-2023.issues.json"
    retrieval.write_text(retrieval.read_text(encoding="utf-8") + " ", encoding="utf-8")

    try:
        finalize_rollout(
            manifest_path=manifest_path,
            state_path=state_path,
            output_root=output_root,
            project_root=project_root,
        )
    except ValueError as error:
        assert "retrieval_sha256" in str(error)
    else:
        raise AssertionError("no debe cerrar con un derivado distinto del estado")
