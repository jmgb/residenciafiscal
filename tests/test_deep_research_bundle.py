"""Bundle C1: snapshot mínimo, determinista y verificable del corpus permitido."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest


def _write(path: Path, content: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode())


def _project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    pdf = project / "sentencias" / "SAN_1_2020.pdf"
    _write(pdf, b"pdf de prueba")
    judgment_id = "san-1-2020"
    _write(project / "knowledge/jurisprudencia-v3/cases/san-1-2020.case.json", "{}\n")
    _write(project / "knowledge/jurisprudencia-v3/verbatim/san-1-2020.pages.json", "{}\n")
    _write(project / "knowledge/jurisprudencia-v3/retrieval/san-1-2020.issues.json", "{}\n")
    _write(project / "knowledge/jurisprudencia-v3/jurisdicciones/san-1-2020.roles.json", "{}\n")
    _write(
        project / "knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json",
        '{"sample_id":"test"}\n',
    )
    _write(project / ".env", "OPENAI_API_KEY=secret\n")
    _write(project / "frontend/should-not-be-included.ts", "secret\n")
    manifest = {
        "schema_version": "residenciafiscal-rollout/1",
        "rollout_id": "rollout-test",
        "expected_documents": 1,
        "documents": [
            {
                "judgment_id": judgment_id,
                "source_file": "sentencias/SAN_1_2020.pdf",
                "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                "proposal_path": "knowledge/jurisprudence-case-proposals/san-1-2020.proposal.json",
                "evaluation_path": "knowledge/jurisprudencia-v3/evaluations/san-1-2020.questions.json",
                "batch_id": "batch-001",
                "risk": "STANDARD",
            }
        ],
    }
    manifest_path = project / "sentencias/jurisprudence_v3_rollout_106.json"
    _write(manifest_path, json.dumps(manifest))
    return project, manifest_path


def test_bundle_contiene_solo_material_permitido_y_hashes_verificables(tmp_path: Path) -> None:
    from deep_research_bundle import build_deep_research_bundle

    project, manifest_path = _project(tmp_path)
    output = tmp_path / "rollout-test.bundle.zip"

    bundle_manifest = build_deep_research_bundle(
        project_root=project,
        rollout_manifest_path=manifest_path,
        output_path=output,
    )

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert names[0] == "MANIFEST.json"
        assert ".env" not in "\n".join(names)
        assert all(not name.startswith("frontend/") for name in names)
        archived_manifest = json.loads(archive.read("MANIFEST.json"))
        assert archived_manifest == bundle_manifest
        for relative_path, expected_sha256 in archived_manifest["files"].items():
            assert hashlib.sha256(archive.read(relative_path)).hexdigest() == expected_sha256

        assert set(names) == {
            "MANIFEST.json",
            "metadata/rollout-manifest.json",
            "cases/san-1-2020.case.json",
            "verbatim/san-1-2020.pages.json",
            "retrieval/san-1-2020.issues.json",
            "retrieval/rollout-106.corpus.json",
            "jurisdicciones/san-1-2020.roles.json",
            "pdf/san-1-2020.pdf",
        }


def test_bundle_es_determinista_y_no_sobrescribe_un_snapshot_existente(tmp_path: Path) -> None:
    from deep_research_bundle import build_deep_research_bundle

    project, manifest_path = _project(tmp_path)
    first = tmp_path / "first.bundle.zip"
    second = tmp_path / "second.bundle.zip"

    build_deep_research_bundle(
        project_root=project,
        rollout_manifest_path=manifest_path,
        output_path=first,
    )
    build_deep_research_bundle(
        project_root=project,
        rollout_manifest_path=manifest_path,
        output_path=second,
    )

    assert first.read_bytes() == second.read_bytes()
    with pytest.raises(FileExistsError):
        build_deep_research_bundle(
            project_root=project,
            rollout_manifest_path=manifest_path,
            output_path=first,
        )


def test_bundle_falla_si_falta_un_artefacto_o_se_altera(tmp_path: Path) -> None:
    from deep_research_bundle import build_deep_research_bundle, verify_deep_research_bundle

    project, manifest_path = _project(tmp_path)
    missing = project / "knowledge/jurisprudencia-v3/cases/san-1-2020.case.json"
    missing.unlink()
    with pytest.raises(FileNotFoundError):
        build_deep_research_bundle(
            project_root=project,
            rollout_manifest_path=manifest_path,
            output_path=tmp_path / "missing.bundle.zip",
        )

    project, manifest_path = _project(tmp_path / "tampered")
    original = tmp_path / "tampered.bundle.zip"
    build_deep_research_bundle(
        project_root=project,
        rollout_manifest_path=manifest_path,
        output_path=original,
    )
    tampered = tmp_path / "tampered-copy.bundle.zip"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, "w") as target:
        for item in source.infolist():
            payload = b"alterado" if item.filename == "pdf/san-1-2020.pdf" else source.read(item)
            target.writestr(item, payload)

    with pytest.raises(ValueError, match="hash"):
        verify_deep_research_bundle(tampered)


def test_deploy_cita_argumentos_remotos_y_restringe_el_bundle_id() -> None:
    script = (
        Path(__file__).resolve().parents[1] / "scripts/deploy_deep_research_bundle.sh"
    ).read_text("utf-8")

    assert '[[ ! "$bundle_id" =~ ^[A-Za-z0-9]' in script
    assert "printf -v REMOTE_INSTALL_COMMAND '%q '" in script
