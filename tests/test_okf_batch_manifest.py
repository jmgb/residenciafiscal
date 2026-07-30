"""Contrato de entrada y CLI para una muestra OKF congelada."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_okf_batch import _inputs, _pages

from export_okf_batch import main
from okf_batch_manifest import load_okf_batch_manifest, validate_batch_sources
from okf_document_builder import load_unique_record
from okf_provenance import sha256_analysis_record, sha256_file


def _write_manifest(
    path: Path,
    *,
    jsonl_path: Path,
    pdf_dir: Path,
    source_files: tuple[str, ...],
) -> None:
    documents = []
    for source_file in source_files:
        record = load_unique_record(jsonl_path, source_file)
        documents.append(
            {
                "source_file": source_file,
                "pdf_sha256": sha256_file(pdf_dir / source_file),
                "analysis_record_sha256": sha256_analysis_record(record),
            }
        )
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "okf-test-5-v1",
                "expected_documents": len(documents),
                "output_schema_version": "residenciafiscal-okf-manifest/3",
                "analysis_jsonl_sha256": sha256_file(jsonl_path),
                "documents": documents,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_valida_cada_pdf_y_registro_antes_de_construir(tmp_path: Path) -> None:
    jsonl_path, pdf_dir, source_files = _inputs(tmp_path)
    manifest_path = tmp_path / "okf-muestra.json"
    _write_manifest(
        manifest_path,
        jsonl_path=jsonl_path,
        pdf_dir=pdf_dir,
        source_files=source_files,
    )
    manifest = load_okf_batch_manifest(manifest_path)

    assert validate_batch_sources(manifest, jsonl_path, pdf_dir) == tuple(sorted(source_files))

    pdf_path = pdf_dir / source_files[0]
    pdf_path.write_bytes(pdf_path.read_bytes() + b"alterado")
    with pytest.raises(ValueError, match="PDF"):
        validate_batch_sources(manifest, jsonl_path, pdf_dir)


def test_rechaza_hashes_invalidos_y_documentos_duplicados(tmp_path: Path) -> None:
    manifest_path = tmp_path / "okf-muestra.json"
    document = {
        "source_file": "sentencia.pdf",
        "pdf_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "analysis_record_sha256": "no-es-un-hash",
    }
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "muestra",
                "expected_documents": 2,
                "output_schema_version": "residenciafiscal-okf-manifest/3",
                "analysis_jsonl_sha256": hashlib.sha256(b"jsonl").hexdigest(),
                "documents": [document, document],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_okf_batch_manifest(manifest_path)


def test_cli_exporta_exclusivamente_la_muestra_del_manifiesto(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    jsonl_path, pdf_dir, source_files = _inputs(tmp_path)
    manifest_path = tmp_path / "okf-muestra.json"
    output_dir = tmp_path / "bundle"
    _write_manifest(
        manifest_path,
        jsonl_path=jsonl_path,
        pdf_dir=pdf_dir,
        source_files=source_files,
    )

    exit_code = main(
        [
            "--jsonl",
            str(jsonl_path),
            "--pdf-dir",
            str(pdf_dir),
            "--output-dir",
            str(output_dir),
            "--manifest",
            str(manifest_path),
        ],
        page_loader=lambda _path: _pages(),
    )

    assert exit_code == 0
    assert len(tuple((output_dir / "sentencias").glob("*.md"))) == 6
    assert "5 sentencias" in capsys.readouterr().out
