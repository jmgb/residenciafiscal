"""Prueba integral del bundle OKF acotado a una sola sentencia."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from test_okf_normalization import _raw_judgment

from citation_models import ExtractedPage
from export_okf import main
from okf_bundle import build_okf_bundle
from okf_normalization import normalize_judgment
from okf_validation import validate_okf_bundle

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_construye_un_bundle_okf_determinista_para_una_sentencia(tmp_path: Path) -> None:
    raw = _raw_judgment()
    other = {**raw, "archivo": "otra.pdf"}
    jsonl_path = tmp_path / "analisis_02012026_155032.jsonl"
    pdf_dir = tmp_path / "sentencias"
    output_dir = tmp_path / "knowledge" / "jurisprudencia"
    annotations_dir = tmp_path / "knowledge" / "annotations"
    pdf_dir.mkdir()
    (pdf_dir / "SAN_1071_2025.pdf").write_bytes(b"%PDF-piloto")
    pdf_hash_before = hashlib.sha256((pdf_dir / "SAN_1071_2025.pdf").read_bytes()).hexdigest()
    jsonl_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in (raw, other)) + "\n",
        encoding="utf-8",
    )
    pages = (
        ExtractedPage(1, "1", "Portada"),
        ExtractedPage(2, "2", "Antecedentes"),
        ExtractedPage(
            3,
            "3",
            "Que radique el núcleo principal de sus actividades o intereses económicos.",
        ),
        ExtractedPage(
            4,
            "4",
            "Movimientos de la tarjeta de crédito en Bescanó, restaurantes y "
            "los de repostaje de gasolina.",
        ),
    )
    judgment = normalize_judgment(raw)
    annotations_dir.mkdir(parents=True)
    annotation_path = annotations_dir / "san-1071-2025.yaml"
    annotation_content = yaml.safe_dump(
        {
            "schema_version": 1,
            "source_file": judgment.archivo,
            "corrections": [],
            "issues": [
                {
                    "id": "residencia-fiscal",
                    "question": "¿Era residente fiscal en España?",
                    "decision": "GANA_AEAT",
                    "status": "proposed",
                    "support_citation_ids": [judgment.citas[0].id],
                    "rationale": "Pendiente de revisión humana.",
                }
            ],
        },
        allow_unicode=True,
        sort_keys=False,
    )
    annotation_path.write_text(annotation_content, encoding="utf-8")

    result = build_okf_bundle(
        jsonl_path=jsonl_path,
        pdf_dir=pdf_dir,
        output_dir=output_dir,
        source_file="SAN_1071_2025.pdf",
        threshold=85,
        annotations_dir=annotations_dir,
        page_loader=lambda _path: pages,
    )
    first_render = {
        path.relative_to(output_dir).as_posix(): path.read_bytes()
        for path in output_dir.rglob("*")
        if path.is_file()
    }
    second_result = build_okf_bundle(
        jsonl_path=jsonl_path,
        pdf_dir=pdf_dir,
        output_dir=output_dir,
        source_file="SAN_1071_2025.pdf",
        threshold=85,
        annotations_dir=annotations_dir,
        page_loader=lambda _path: pages,
    )
    second_render = {
        path.relative_to(output_dir).as_posix(): path.read_bytes()
        for path in output_dir.rglob("*")
        if path.is_file()
    }
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.document_path == output_dir / "sentencias" / "san-1071-2025.md"
    assert result.document_count == 1
    assert result.literal_citation_count == 1
    assert result.pending_citation_count == 5
    assert manifest["schema_version"] == "residenciafiscal-okf-manifest/2"
    assert manifest["okf_version"] == "0.2"
    assert manifest["scope"]["documents"] == 1
    assert manifest["documents"][0]["concept_id"] == "sentencias/san-1071-2025"
    assert manifest["documents"][0]["legal_issues"] == {
        "approved": 0,
        "proposed": 1,
    }
    assert manifest["analysis_provenance"]["prompt_sha256"] is None
    assert manifest["analysis_provenance"]["model_id"] == "not_recorded"
    assert manifest["pdf_sources"][0]["extractor"].startswith("pypdf/")
    assert (
        json.loads(
            (output_dir / "sources" / "san-1071-2025.analysis.json").read_text(encoding="utf-8")
        )
        == raw
    )
    assert set(first_render) == {
        "index.md",
        "manifest.json",
        "sentencias/index.md",
        "sentencias/san-1071-2025.md",
        "sources/san-1071-2025.analysis.json",
    }
    assert second_result == result
    assert second_render == first_render
    assert (
        hashlib.sha256((pdf_dir / "SAN_1071_2025.pdf").read_bytes()).hexdigest() == pdf_hash_before
    )
    assert validate_okf_bundle(output_dir) == ()
    annotation_path.write_text(annotation_content + "\n", encoding="utf-8")
    assert any(
        "hash de anotaciones no coincide" in issue for issue in validate_okf_bundle(output_dir)
    )
    annotation_path.write_text(annotation_content, encoding="utf-8")
    assert validate_okf_bundle(output_dir) == ()
    snapshot_path = output_dir / "sources" / "san-1071-2025.analysis.json"
    snapshot_path.write_text(
        snapshot_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    assert any(
        "hash del registro de análisis no coincide" in issue
        for issue in validate_okf_bundle(output_dir)
    )


def test_cli_exporta_exclusivamente_la_sentencia_indicada(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = _raw_judgment()
    jsonl_path = tmp_path / "analisis.jsonl"
    pdf_dir = tmp_path / "sentencias"
    output_dir = tmp_path / "bundle"
    pdf_dir.mkdir()
    (pdf_dir / "SAN_1071_2025.pdf").write_bytes(b"%PDF-piloto")
    jsonl_path.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    pages = (
        "Portada",
        "Antecedentes",
        "Núcleo principal de sus actividades o intereses económicos.",
        "Movimientos de la tarjeta de crédito en Bescanó, restaurantes y "
        "los de repostaje de gasolina.",
    )

    exit_code = main(
        [
            "--jsonl",
            str(jsonl_path),
            "--pdf-dir",
            str(pdf_dir),
            "--output-dir",
            str(output_dir),
            "--source-file",
            "SAN_1071_2025.pdf",
            "--threshold",
            "85",
        ],
        page_loader=lambda _path: pages,
    )

    assert exit_code == 0
    assert (output_dir / "sentencias" / "san-1071-2025.md").is_file()
    assert "1 sentencia" in capsys.readouterr().out


def test_detecta_si_un_documento_deja_de_coincidir_con_el_manifiesto(
    tmp_path: Path,
) -> None:
    raw = _raw_judgment()
    jsonl_path = tmp_path / "analisis.jsonl"
    pdf_dir = tmp_path / "sentencias"
    output_dir = tmp_path / "bundle"
    pdf_dir.mkdir()
    (pdf_dir / "SAN_1071_2025.pdf").write_bytes(b"%PDF-piloto")
    jsonl_path.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    pages = (
        "Portada",
        "Antecedentes",
        "Núcleo principal de sus actividades o intereses económicos.",
        "Movimientos de la tarjeta de crédito en Bescanó, restaurantes y "
        "los de repostaje de gasolina.",
    )
    result = build_okf_bundle(
        jsonl_path=jsonl_path,
        pdf_dir=pdf_dir,
        output_dir=output_dir,
        source_file="SAN_1071_2025.pdf",
        threshold=85,
        page_loader=lambda _path: pages,
    )
    result.document_path.write_text(
        result.document_path.read_text(encoding="utf-8") + "\nCambio manual.\n",
        encoding="utf-8",
    )

    assert any(
        "hash de documento no coincide" in issue for issue in validate_okf_bundle(output_dir)
    )


def test_el_bundle_piloto_versionado_es_valido() -> None:
    bundle_dir = REPOSITORY_ROOT / "knowledge" / "jurisprudencia"
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))

    assert validate_okf_bundle(bundle_dir) == ()
    assert manifest["scope"] == {
        "documents": 1,
        "source_files": ["SAN_1071_2025.pdf"],
    }
    assert manifest["documents"][0]["literal_citations"] == 12
    assert manifest["documents"][0]["pending_citations"] == 5
    assert manifest["documents"][0]["legal_issues"] == {
        "approved": 0,
        "proposed": 3,
    }
