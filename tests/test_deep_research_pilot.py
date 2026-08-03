"""Preflight y comando seguro del piloto C2."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_deep_research_bundle import _project, _write


def _source() -> dict[str, object]:
    return {
        "schema_version": "residenciafiscal-chat-f02-dev-set/1",
        "source_resource": "knowledge/jurisprudencia-v3/evaluations/chat-question-pilot-5.bank.json",
        "questions": [
            {
                "question_id": "GEN-01",
                "dimension": "general",
                "expected_behavior": "responder",
                "question": "¿Qué tiene en cuenta Hacienda para demostrar la residencia?",
            },
            {
                "question_id": "DAY-01",
                "dimension": "caso_particular_incompleto",
                "expected_behavior": "preguntar",
                "question": "Digo que pasé menos de 183 días, ¿qué usaría Hacienda?",
            },
        ],
    }


def _holdout() -> dict[str, object]:
    return {
        "schema_version": "residenciafiscal-retrieval-evaluation-bank/1",
        "source_resource": "docs/experiments/CHAT_QUESTION_HOLDOUT_E.json",
        "questions": [
            {
                "question_id": "HE-OTHER-01",
                "question": "¿Qué combinación de señales ha utilizado Hacienda?",
                "behavior": "responder",
                "expected_judgment_ids": [],
                "contrast_judgment_ids": [],
            }
        ],
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    project, manifest = _project(tmp_path)
    source = project / "docs/experiments/CHAT_STRATEGY_F02_DEV_SET.json"
    holdout = project / "docs/experiments/CHAT_QUESTION_HOLDOUT_E.json"
    _write(source, json.dumps(_source(), ensure_ascii=False))
    _write(holdout, json.dumps(_holdout(), ensure_ascii=False))
    spec = project / "docs/experiments/CHAT_DEEP_RESEARCH_C2_PILOT.json"
    _write(
        spec,
        json.dumps(
            {
                "schema_version": "residenciafiscal-deep-research-pilot/1",
                "pilot_id": "c2-2026-08-03",
                "source_resource": "docs/experiments/CHAT_STRATEGY_F02_DEV_SET.json",
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "holdout_resource": "docs/experiments/CHAT_QUESTION_HOLDOUT_E.json",
                "holdout_sha256": hashlib.sha256(holdout.read_bytes()).hexdigest(),
                "question_ids": ["GEN-01", "DAY-01"],
            },
            ensure_ascii=False,
        ),
    )
    bundle = tmp_path / "bundle.zip"
    from deep_research_bundle import build_deep_research_bundle

    build_deep_research_bundle(
        project_root=project,
        rollout_manifest_path=manifest,
        output_path=bundle,
    )
    return project, spec, source, holdout, bundle


def test_prepare_materializa_jobs_y_bloquea_el_holdout(tmp_path: Path) -> None:
    from deep_research_pilot import prepare_pilot

    project, spec, source, holdout, bundle = _fixture(tmp_path)
    output = tmp_path / "prepared"
    plan = prepare_pilot(
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=output,
    )

    assert plan.bundle_id == "rollout-106/1"
    assert [item.question_id for item in plan.questions] == ["GEN-01", "DAY-01"]
    assert [item.job_id for item in plan.jobs] == ["c2-2026-08-03-01", "c2-2026-08-03-02"]
    assert json.loads((output / "PLAN.json").read_text()) == plan.model_dump(mode="json")
    assert (output / "jobs/c2-2026-08-03-01.json").is_file()


def test_prepare_rechaza_pregunta_que_coincide_con_holdout(tmp_path: Path) -> None:
    from deep_research_pilot import prepare_pilot

    project, spec, source, holdout, bundle = _fixture(tmp_path)
    source_data: dict[str, Any] = json.loads(source.read_text())
    holdout_questions = _holdout()["questions"]
    assert isinstance(holdout_questions, list)
    holdout_question = holdout_questions[0]
    assert isinstance(holdout_question, dict)
    source_data["questions"][0]["question"] = holdout_question["question"]
    _write(source, json.dumps(source_data, ensure_ascii=False))
    spec_data = json.loads(spec.read_text())
    spec_data["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    _write(spec, json.dumps(spec_data, ensure_ascii=False))

    with pytest.raises(ValueError, match="holdout"):
        prepare_pilot(
            project_root=project,
            spec_path=spec,
            source_path=source,
            holdout_path=holdout,
            bundle_path=bundle,
            output_dir=tmp_path / "rejected",
        )


def test_comando_codex_es_no_interactivo_y_solo_lectura(tmp_path: Path) -> None:
    from deep_research_contracts import DeepResearchJob
    from deep_research_pilot import codex_command

    job = DeepResearchJob(
        schema_version="residenciafiscal-deep-research-job/1",
        job_id="c2-job-01",
        request_id="c2-job-01",
        bundle_id="rollout-106/1",
        question="Pregunta de prueba",
    )
    command = codex_command(
        job=job,
        workspace=tmp_path / "workspace",
        schema_path=tmp_path / "schema.json",
        output_path=tmp_path / "answer.json",
    )

    assert command[0] == "bwrap"
    assert "--unshare-all" in command
    assert "--unshare-net" in command
    assert command[command.index("--ro-bind") + 2] == "/usr"
    assert "/workspace" in command
    assert "/codex-home/auth.json" not in command
    assert command[command.index("--") + 1].endswith("/codex.js")
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--skip-git-repo-check" in command
    assert "--json" in command
    assert "--search" not in command
    assert "--dangerously-bypass-approvals-and-sandbox" not in command


def test_run_fail_closed_hasta_disponer_del_worker_autenticado(tmp_path: Path) -> None:
    from deep_research_pilot import prepare_pilot, run_pilot

    project, spec, source, holdout, bundle = _fixture(tmp_path)
    prepared = tmp_path / "prepared"
    prepare_pilot(
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
    )

    with pytest.raises(RuntimeError, match="worker autenticado"):
        run_pilot(
            plan_path=prepared / "PLAN.json",
            project_root=project,
            spec_path=spec,
            source_path=source,
            holdout_path=holdout,
            bundle_path=bundle,
            output_dir=prepared,
            input_cost_microusd_per_million=1_000_000,
            output_cost_microusd_per_million=1_000_000,
        )


def test_run_pilot_solo_persiste_la_salida_estructurada(tmp_path: Path) -> None:
    from deep_research_contracts import DeepResearchLimits
    from deep_research_pilot import prepare_pilot, run_pilot

    project, spec, source, holdout, bundle = _fixture(tmp_path)
    prepared = tmp_path / "prepared"
    limits = DeepResearchLimits(timeout_ms=1_000, max_turns=2)
    prepare_pilot(
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
        limits=limits,
    )
    fake_codex = tmp_path / "fake_codex.py"
    _write(
        fake_codex,
        """
import json
import re
import sys
from pathlib import Path

answer_path = Path(sys.argv[sys.argv.index('--output-last-message') + 1])
job_id = re.search(r'job_id debe ser "([^"]+)"', sys.argv[-1]).group(1)
print(json.dumps({'type': 'turn.started'}))
print(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'printf ok'}}))
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 5}}))
answer_path.write_text(json.dumps({
    'schema_version': 'residenciafiscal-deep-research-output/1',
    'job_id': job_id,
    'request_id': job_id,
    'status': 'pregunta',
    'text': 'Salida sintética de prueba',
    'limits': [],
    'claims': [],
    'evidence': [],
    'cost_microusd': 100,
    'cost_measurement': 'ESTIMATED',
    'model': 'fake',
}), encoding='utf-8')
""".strip(),
    )

    results = run_pilot(
        plan_path=prepared / "PLAN.json",
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
        codex_binary=f"{sys.executable} {fake_codex}",
        sandbox_binary=None,
        input_cost_microusd_per_million=1_000_000,
        output_cost_microusd_per_million=1_000_000,
    )

    assert [item.status for item in results] == ["pregunta", "pregunta"]
    assert [item.cost_microusd for item in results] == [15, 15]
    assert (prepared / "results/c2-2026-08-03-01.json").is_file()
    assert not list(prepared.glob("**/rollout-*"))


def test_run_corta_codex_al_superar_turnos(tmp_path: Path) -> None:
    from deep_research_contracts import DeepResearchLimits
    from deep_research_pilot import prepare_pilot, run_pilot

    project, spec, source, holdout, bundle = _fixture(tmp_path)
    prepared = tmp_path / "prepared"
    prepare_pilot(
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
        limits=DeepResearchLimits(timeout_ms=5_000, max_turns=1),
    )
    fake_codex = tmp_path / "fake_codex.py"
    _write(
        fake_codex,
        """
import json
import time

print(json.dumps({'type': 'turn.started'}), flush=True)
print(json.dumps({'type': 'turn.started'}), flush=True)
time.sleep(10)
""".strip(),
    )

    results = run_pilot(
        plan_path=prepared / "PLAN.json",
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
        codex_binary=f"{sys.executable} {fake_codex}",
        sandbox_binary=None,
        input_cost_microusd_per_million=1_000_000,
        output_cost_microusd_per_million=1_000_000,
    )

    assert [item.limits for item in results] == [("max_turns",), ("max_turns",)]


def test_run_corta_codex_al_superar_documentos_leidos(tmp_path: Path) -> None:
    from deep_research_contracts import DeepResearchLimits
    from deep_research_pilot import prepare_pilot, run_pilot

    project, spec, source, holdout, bundle = _fixture(tmp_path)
    prepared = tmp_path / "prepared"
    prepare_pilot(
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
        limits=DeepResearchLimits(timeout_ms=5_000, max_turns=5, max_documents=1),
    )
    fake_codex = tmp_path / "fake_codex.py"
    _write(
        fake_codex,
        """
import json
import time

print(json.dumps({'type': 'turn.started'}), flush=True)
print(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'cat cases/san-a-2020.case.json'}}), flush=True)
print(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'cat cases/san-b-2020.case.json'}}), flush=True)
time.sleep(10)
""".strip(),
    )

    results = run_pilot(
        plan_path=prepared / "PLAN.json",
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
        codex_binary=f"{sys.executable} {fake_codex}",
        sandbox_binary=None,
        input_cost_microusd_per_million=1_000_000,
        output_cost_microusd_per_million=1_000_000,
    )

    assert [item.limits for item in results] == [
        ("max_documents_read",),
        ("max_documents_read",),
    ]


def test_auditoria_falla_cerrado_ante_lectura_indirecta(tmp_path: Path) -> None:
    from deep_research_pilot import _resource_delta

    project, _, _, _, _ = _fixture(tmp_path)
    event = {
        "type": "item.started",
        "item": {
            "type": "command_execution",
            "command": "python -c \"from pathlib import Path; print(Path('/workspace').rglob('*'))\"",
        },
    }

    documents, pages, audit_failed = _resource_delta(event, project)

    assert documents == set()
    assert pages == set()
    assert audit_failed


def test_indice_agregado_valido_no_consume_presupuesto_de_documentos(tmp_path: Path, monkeypatch):
    from deep_research_pilot import _resource_delta

    project, _, _, _, _ = _fixture(tmp_path)
    _write(project / "retrieval/rollout-106.corpus.json", b"{}")
    monkeypatch.setattr(
        "deep_research_pilot.load_retrieval_corpus",
        lambda _: SimpleNamespace(sources=(), units=()),
    )
    event = {
        "type": "item.started",
        "item": {
            "type": "command_execution",
            "command": "cat retrieval/rollout-106.corpus.json",
        },
    }

    documents, pages, audit_failed = _resource_delta(event, project)

    assert documents == set()
    assert pages == set()
    assert not audit_failed


def test_run_rechaza_un_plan_editado_despues_del_preflight(tmp_path: Path) -> None:
    from deep_research_pilot import prepare_pilot, run_pilot

    project, spec, source, holdout, bundle = _fixture(tmp_path)
    prepared = tmp_path / "prepared"
    prepare_pilot(
        project_root=project,
        spec_path=spec,
        source_path=source,
        holdout_path=holdout,
        bundle_path=bundle,
        output_dir=prepared,
    )
    plan_data = json.loads((prepared / "PLAN.json").read_text())
    plan_data["jobs"][0]["question"] = "Pregunta alterada"
    _write(prepared / "PLAN.json", json.dumps(plan_data, ensure_ascii=False))

    with pytest.raises(ValueError, match="PLAN.json"):
        run_pilot(
            plan_path=prepared / "PLAN.json",
            project_root=project,
            spec_path=spec,
            source_path=source,
            holdout_path=holdout,
            bundle_path=bundle,
            output_dir=prepared,
            input_cost_microusd_per_million=1_000_000,
            output_cost_microusd_per_million=1_000_000,
        )


def test_evidencia_sin_verbatim_no_puede_pasar_el_gate(tmp_path: Path) -> None:
    from deep_research_contracts import (
        DeepResearchClaim,
        DeepResearchEvidence,
        DeepResearchOutput,
    )
    from deep_research_pilot import validate_output_evidence

    output = DeepResearchOutput(
        schema_version="residenciafiscal-deep-research-output/1",
        job_id="c2-job-01",
        request_id="c2-job-01",
        status="completa",
        text="Respuesta",
        limits=(),
        claims=(DeepResearchClaim(text="Afirmación", evidence_indexes=(1,)),),
        evidence=(
            DeepResearchEvidence(
                judgment_id="san-1-2020",
                page=1,
                source_sha256="a" * 64,
                quote="cita inventada",
                verification="EXACT",
            ),
        ),
        cost_microusd=100,
        cost_measurement="ESTIMATED",
    )

    assert not validate_output_evidence(output, tmp_path)


def test_salida_sustantiva_sin_evidencia_no_puede_pasar_el_gate() -> None:
    from deep_research_contracts import DeepResearchOutput

    with pytest.raises(ValueError, match="sustantiva exige claims y evidence"):
        DeepResearchOutput(
            schema_version="residenciafiscal-deep-research-output/1",
            job_id="c2-job-01",
            request_id="c2-job-01",
            status="completa",
            text="Respuesta jurídica sin respaldo",
            limits=(),
            claims=(),
            evidence=(),
        )
