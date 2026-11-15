"""Revalidación completa desde un clon sin entradas históricas de output/."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from okf_provenance import sha256_file
from verbatim_artifact import write_verbatim_corpus
from verbatim_extraction import extract_verbatim_corpus


@pytest.fixture
def corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    manifest = tmp_path / "sentencias/rollout.json"
    verbatim = tmp_path / "knowledge/verbatim"
    manifest.parent.mkdir()
    documents = []
    for index, document_id in enumerate(("primero", "segundo"), start=1):
        pdf = manifest.parent / f"{document_id}.pdf"
        writer = PdfWriter()
        for _ in range(index):
            writer.add_blank_page(width=200, height=200)
        writer.write(pdf)
        source_file = pdf.relative_to(tmp_path).as_posix()
        write_verbatim_corpus(
            extract_verbatim_corpus(
                pdf,
                document_id=document_id,
                source_file=source_file,
                extractor_version="historical",
            ),
            verbatim / f"{document_id}.pages.json",
        )
        documents.append(
            {
                "judgment_id": document_id,
                "source_file": source_file,
                "source_sha256": sha256_file(pdf),
                "proposal_path": f"output/{document_id}.proposal.json",
                "evaluation_path": f"output/{document_id}.questions.json",
                "batch_id": "batch-01",
                "risk": "STANDARD",
            }
        )
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-rollout/1",
                "rollout_id": "test",
                "expected_documents": 2,
                "documents": documents,
            }
        )
    )
    return tmp_path, manifest, verbatim


def test_revalida_todos_sin_output_y_sin_escribir(corpus: tuple[Path, Path, Path]) -> None:
    from validate_verbatim_corpus import validate_verbatim_corpus

    root, manifest, verbatim = corpus
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    results = validate_verbatim_corpus(
        project_root=root, manifest_path=manifest, verbatim_root=verbatim
    )

    assert [result.document_id for result in results] == ["primero", "segundo"]
    assert sum(result.page_count for result in results) == 3
    assert not (root / "output").exists()
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_rechaza_un_pdf_modificado_fuera_del_piloto(corpus: tuple[Path, Path, Path]) -> None:
    from validate_verbatim_corpus import validate_verbatim_corpus

    root, manifest, verbatim = corpus
    (root / "sentencias/segundo.pdf").write_bytes(b"PDF modificado")
    with pytest.raises(ValueError, match="source_sha256"):
        validate_verbatim_corpus(project_root=root, manifest_path=manifest, verbatim_root=verbatim)


def test_rechaza_un_artefacto_que_falta(corpus: tuple[Path, Path, Path]) -> None:
    from validate_verbatim_corpus import validate_verbatim_corpus

    root, manifest, verbatim = corpus
    (verbatim / "segundo.pages.json").unlink()
    with pytest.raises(ValueError, match="cobertura"):
        validate_verbatim_corpus(project_root=root, manifest_path=manifest, verbatim_root=verbatim)


def test_rechaza_una_identidad_ajena_al_manifiesto(corpus: tuple[Path, Path, Path]) -> None:
    from validate_verbatim_corpus import validate_verbatim_corpus

    root, manifest, verbatim = corpus
    (verbatim / "segundo.pages.json").write_bytes((verbatim / "primero.pages.json").read_bytes())
    with pytest.raises(ValueError, match="segundo.*manifiesto"):
        validate_verbatim_corpus(project_root=root, manifest_path=manifest, verbatim_root=verbatim)


def test_rechaza_el_hash_incorrecto_del_manifiesto(corpus: tuple[Path, Path, Path]) -> None:
    from validate_verbatim_corpus import validate_verbatim_corpus

    root, manifest, verbatim = corpus
    data = json.loads(manifest.read_text())
    data["documents"][1]["source_sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="segundo.*manifiesto"):
        validate_verbatim_corpus(project_root=root, manifest_path=manifest, verbatim_root=verbatim)


def test_cli_informa_documentos_y_paginas(
    corpus: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    from validate_verbatim_corpus import main

    root, manifest, verbatim = corpus
    assert (
        main(
            [
                "--project-root",
                str(root),
                "--manifest",
                str(manifest),
                "--verbatim-root",
                str(verbatim),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "documents": 2,
        "pages": 3,
        "validation": "passed",
    }
