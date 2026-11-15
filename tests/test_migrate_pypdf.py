"""Migración del extractor sin cambiar texto jurídico ni publicar lotes parciales."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from jurisprudence_case_v3_factory import valid_case
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from jurisprudence_case_catalogs import LegalReviewState
from okf_provenance import sha256_file

OUTPUT = Path("knowledge/jurisprudencia-v3")
MANIFEST = Path("sentencias/jurisprudence_v3_rollout_106.json")
SAMPLE = Path("sentencias/jurisprudence_v3_sample_5.json")
STATE = Path("output/jurisprudence-v3-rollout-state.json")
JUDGMENT = "san-1210-2023"


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    from export_jurisprudence_sample import export_jurisprudence_sample
    from jurisprudence_retrieval_corpus import build_retrieval_corpus, render_retrieval_corpus
    from jurisprudence_rollout import initialize_rollout, write_rollout_state
    from jurisprudence_rollout_completion import finalize_rollout
    from jurisprudence_rollout_models import RolloutExecutionStatus
    from jurisprudence_sample_quality import (
        build_sample_quality_report,
        render_sample_quality_report,
    )

    pdf_path = tmp_path / "sentencias/SAN_1210_2023.pdf"
    pdf_path.parent.mkdir()
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                        }
                    )
                }
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 10 100 Td (tiene su residencia efectiva) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(pdf_path)
    proposal_path = Path(f"knowledge/proposals/{JUDGMENT}.json")
    evaluation_path = OUTPUT / f"evaluations/{JUDGMENT}.questions.json"
    proposal = valid_case()
    proposal["judgment"]["source_file"] = pdf_path.relative_to(tmp_path).as_posix()
    proposal["judgment"]["analysis_provenance"]["input_artifacts"] = [
        {"kind": "VERBATIM", "source_path": f"{OUTPUT}/verbatim/{JUDGMENT}.pages.json"},
        {"kind": "ANNOTATIONS", "source_path": "knowledge/annotations/review.yaml"},
    ]
    _write_json(tmp_path / "knowledge/annotations/review.yaml", {"status": "proposed"})
    proposal["source_anchors"][0]["fragments"][0]["page_index"] = 1
    _write_json(tmp_path / proposal_path, proposal)
    _write_json(
        tmp_path / evaluation_path,
        {
            "schema_version": "residenciafiscal-case-question-evaluation/1",
            "judgment_id": JUDGMENT,
            "questions": [
                {
                    "question_id": "q1",
                    "question": "¿Residente en España?",
                    "required_issue_ids": ["residencia-fiscal"],
                    "required_fact_ids": [],
                    "required_evidence_ids": [],
                    "required_anchor_ids": ["anchor-residencia-conclusion"],
                    "expected_behavior": "responder",
                    "limitations": "Borrador de agente.",
                }
            ],
        },
    )
    document = {
        "judgment_id": JUDGMENT,
        "source_file": pdf_path.relative_to(tmp_path).as_posix(),
        "source_sha256": sha256_file(pdf_path),
        "proposal_path": proposal_path.as_posix(),
        "evaluation_path": evaluation_path.as_posix(),
    }
    _write_json(
        tmp_path / SAMPLE,
        {
            "schema_version": "residenciafiscal-jurisprudence-sample/1",
            "sample_id": "sample-prueba",
            "expected_documents": 1,
            "documents": [document],
        },
    )
    _write_json(
        tmp_path / MANIFEST,
        {
            "schema_version": "residenciafiscal-rollout/1",
            "rollout_id": "rollout-prueba",
            "expected_documents": 1,
            "documents": [
                {
                    **document,
                    "batch_id": "batch-001",
                    "risk": "HIGH",
                    "proposal_sha256": sha256_file(tmp_path / proposal_path),
                    "evaluation_sha256": sha256_file(tmp_path / evaluation_path),
                }
            ],
        },
    )
    output = tmp_path / OUTPUT
    export_jurisprudence_sample(
        manifest_path=tmp_path / SAMPLE, output_root=output, project_root=tmp_path
    )
    record = json.loads((output / "sample-build.json").read_bytes())["documents"][0]
    state = initialize_rollout(tmp_path / MANIFEST)
    state = state.model_copy(
        update={
            "documents": (
                state.documents[0].model_copy(
                    update={
                        **{
                            k: record[k]
                            for k in (
                                "case_sha256",
                                "retrieval_sha256",
                                "markdown_sha256",
                                "verbatim_sha256",
                            )
                        },
                        "attempts": 2,
                        "execution_status": RolloutExecutionStatus.BUILD_PASSED,
                        "legal_review": LegalReviewState.AGENT_REVIEWED,
                    }
                ),
            )
        }
    )
    write_rollout_state(state, tmp_path / STATE)
    finalize_rollout(
        manifest_path=tmp_path / MANIFEST,
        state_path=tmp_path / STATE,
        output_root=output,
        project_root=tmp_path,
    )
    case_path = output / f"cases/{JUDGMENT}.case.json"
    quality = build_sample_quality_report(
        (case_path,), sample_id="sample-prueba", project_root=tmp_path
    )
    (output / "reports/sample-5.quality.json").write_text(render_sample_quality_report(quality))
    corpus = build_retrieval_corpus(
        (output / f"retrieval/{JUDGMENT}.issues.json",),
        sample_id="sample-prueba",
        project_root=tmp_path,
    )
    (output / "retrieval/corpus.json").write_text(render_retrieval_corpus(corpus))
    (output / "reports/historical.json").write_text('{"observacion_historica": true}\n')
    return tmp_path


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _new_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("verbatim_extraction.version", lambda _: "next-version")
    monkeypatch.setattr("verbatim_validation.version", lambda _: "next-version")


def test_migra_y_revalida_procedencia_sin_alterar_revisiones(project: Path, monkeypatch) -> None:
    from jurisprudence_rollout_completion import finalize_rollout
    from migrate_pypdf import migrate_pypdf

    before = _snapshot(project)
    _new_version(monkeypatch)
    result = migrate_pypdf(project_root=project)

    assert result.document_count == 1
    assert result.page_count == 1
    assert result.changed_file_count > 0
    original = json.loads(before[f"{OUTPUT}/verbatim/{JUDGMENT}.pages.json"])
    current = json.loads((project / OUTPUT / f"verbatim/{JUDGMENT}.pages.json").read_bytes())
    assert current["pages"] == original["pages"]
    assert current["extractor"]["version"] == "next-version"
    state = json.loads((project / STATE).read_bytes())
    assert state["documents"][0]["attempts"] == 2
    assert state["documents"][0]["legal_review"] == "AGENT_REVIEWED"
    assert (
        finalize_rollout(
            manifest_path=project / MANIFEST,
            state_path=project / STATE,
            output_root=project / OUTPUT,
            project_root=project,
        ).publication_status
        == "AGENT_REVIEWED_ONLY"
    )
    assert (project / OUTPUT / "reports/historical.json").read_bytes() == before[
        f"{OUTPUT}/reports/historical.json"
    ]
    assert str(project) not in (project / OUTPUT / "sample-build.json").read_text()
    assert migrate_pypdf(project_root=project).changed_file_count == 0


def test_aborta_sin_escribir_si_cambia_texto(project: Path, monkeypatch) -> None:
    import verbatim_extraction
    from migrate_pypdf import migrate_pypdf

    before = _snapshot(project)
    original = verbatim_extraction._build_page
    monkeypatch.setattr(
        verbatim_extraction, "_build_page", lambda index, text: original(index, text + " alterado")
    )
    with pytest.raises(ValueError, match="san-1210-2023.*página 1"):
        migrate_pypdf(project_root=project)
    assert _snapshot(project) == before


def test_check_no_publica_y_error_de_compilacion_no_deja_cambios(
    project: Path, monkeypatch
) -> None:
    from migrate_pypdf import migrate_pypdf

    before = _snapshot(project)
    _new_version(monkeypatch)
    result = migrate_pypdf(project_root=project, check_only=True)
    assert result.page_count == 1
    assert _snapshot(project) == before

    def fail(*args, **kwargs):
        raise ValueError("fallo de compilación")

    monkeypatch.setattr("export_jurisprudence_sample.export_jurisprudence_case", fail)
    with pytest.raises(ValueError, match="fallo de compilación"):
        migrate_pypdf(project_root=project)
    assert _snapshot(project) == before


def test_rechaza_hash_de_propuesta_obsoleta(project: Path, monkeypatch) -> None:
    from migrate_pypdf import migrate_pypdf

    proposal = project / f"knowledge/proposals/{JUDGMENT}.json"
    proposal.write_bytes(proposal.read_bytes() + b"\n")
    before = _snapshot(project)
    _new_version(monkeypatch)
    with pytest.raises(ValueError, match="proposal_sha256"):
        migrate_pypdf(project_root=project)
    assert _snapshot(project) == before


def test_no_publica_cambios_juridicos_del_compilador(project: Path, monkeypatch) -> None:
    import jurisprudence_case_compilation
    from migrate_pypdf import migrate_pypdf

    before = _snapshot(project)
    original = jurisprudence_case_compilation.compile_case_proposal

    def altered(*args, **kwargs):
        case = original(*args, **kwargs)
        return case.model_copy(
            update={
                "holdings": (
                    case.holdings[0].model_copy(update={"conclusion": "Conclusión alterada"}),
                )
            }
        )

    monkeypatch.setattr(jurisprudence_case_compilation, "compile_case_proposal", altered)
    with pytest.raises(ValueError, match="contenido jurídico"):
        migrate_pypdf(project_root=project)
    assert _snapshot(project) == before


@pytest.mark.parametrize(
    "resource,error",
    [
        (f"knowledge/proposals/{JUDGMENT}.json", "proposal_sha256"),
        ("knowledge/annotations/review.yaml", "input_artifacts hash"),
    ],
)
def test_preserva_entrada_editada_durante_el_build(
    project: Path, monkeypatch, resource, error
) -> None:
    import export_jurisprudence_sample
    from migrate_pypdf import migrate_pypdf

    before = _snapshot(project)
    _new_version(monkeypatch)
    proposal = Path(resource)
    exporter = export_jurisprudence_sample.export_jurisprudence_case

    def concurrent_edit(*args, **kwargs):
        result = exporter(*args, **kwargs)
        (project / proposal).write_bytes(before[proposal.as_posix()] + b"\n")
        return result

    monkeypatch.setattr(export_jurisprudence_sample, "export_jurisprudence_case", concurrent_edit)
    with pytest.raises(ValueError, match=error):
        migrate_pypdf(project_root=project)
    expected = dict(before)
    expected[proposal.as_posix()] += b"\n"
    assert _snapshot(project) == expected


def test_no_publica_cambios_de_recuperacion(project: Path, monkeypatch) -> None:
    import export_jurisprudence_case_derivatives
    from migrate_pypdf import migrate_pypdf

    before = _snapshot(project)
    original = export_jurisprudence_case_derivatives.build_retrieval_index

    def altered(*args, **kwargs):
        index = original(*args, **kwargs)
        return index.model_copy(
            update={
                "units": (
                    index.units[0].model_copy(
                        update={"search_text": "Texto diferente para búsqueda"}
                    ),
                )
            }
        )

    monkeypatch.setattr(export_jurisprudence_case_derivatives, "build_retrieval_index", altered)
    with pytest.raises(ValueError, match="índice de recuperación"):
        migrate_pypdf(project_root=project)
    assert _snapshot(project) == before


def test_restaura_archivos_si_falla_una_publicacion(project: Path, monkeypatch) -> None:
    import migrate_pypdf

    before = _snapshot(project)
    _new_version(monkeypatch)
    writer = migrate_pypdf.write_case_derivative
    calls = 0

    def failing_writer(data, path):
        nonlocal calls
        if path.is_relative_to(project):
            calls += 1
            if calls == 2:
                raise OSError("fallo al publicar")
        return writer(data, path)

    monkeypatch.setattr(migrate_pypdf, "write_case_derivative", failing_writer)
    with pytest.raises(OSError, match="fallo al publicar"):
        migrate_pypdf.migrate_pypdf(project_root=project)
    assert calls >= 3
    assert _snapshot(project) == before


def test_cli_y_target_make_exponen_modo_check(project: Path, capsys) -> None:
    from migrate_pypdf import main

    before = _snapshot(project)
    assert main(["--project-root", str(project), "--check"]) == 0
    assert json.loads(capsys.readouterr().out)["check_only"] is True
    assert _snapshot(project) == before
    result = subprocess.run(
        ["make", "-n", "migrate-pypdf", "PYPDF_MIGRATION_ARGS=--check"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "uv run python src/migrate_pypdf.py" in result.stdout
    assert "--check" in result.stdout
