"""Construcción atómica y determinista de la muestra OKF."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_okf_normalization import _raw_judgment

from citation_models import ExtractedPage
from okf_batch import build_okf_batch
from okf_validation import validate_okf_bundle


def _pages() -> tuple[ExtractedPage, ...]:
    return (
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
        ExtractedPage(
            5,
            "5",
            "Ciertamente la Administración ha acreditado la residencia.",
        ),
    )


def _inputs(tmp_path: Path) -> tuple[Path, Path, tuple[str, ...]]:
    source_files = tuple(f"SAN_{number}_2025.pdf" for number in (5, 3, 1, 4, 2))
    records = []
    pdf_dir = tmp_path / "sentencias"
    pdf_dir.mkdir()
    for index, source_file in enumerate(source_files, 1):
        raw = _raw_judgment()
        raw["archivo"] = source_file
        raw["identificadores"] = {
            "ROJ": f"SAN {index}/2025",
            "ECLI": f"ECLI:ES:AN:2025:{index}",
        }
        records.append(raw)
        (pdf_dir / source_file).write_bytes(f"%PDF-{index}".encode())
    jsonl_path = tmp_path / "analisis.jsonl"
    jsonl_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return jsonl_path, pdf_dir, source_files


def _snapshot(output_dir: Path) -> dict[str, bytes]:
    return {
        path.relative_to(output_dir).as_posix(): path.read_bytes()
        for path in output_dir.rglob("*")
        if path.is_file()
    }


def test_construye_cinco_documentos_en_orden_y_de_forma_determinista(
    tmp_path: Path,
) -> None:
    jsonl_path, pdf_dir, source_files = _inputs(tmp_path)
    first_output = tmp_path / "bundle-a"
    second_output = tmp_path / "bundle-b"

    first = build_okf_batch(
        jsonl_path=jsonl_path,
        pdf_dir=pdf_dir,
        output_dir=first_output,
        source_files=source_files,
        threshold=85,
        page_loader=lambda _path: _pages(),
    )
    second = build_okf_batch(
        jsonl_path=jsonl_path,
        pdf_dir=pdf_dir,
        output_dir=second_output,
        source_files=reversed(source_files),
        threshold=85,
        page_loader=lambda _path: _pages(),
    )
    manifest = json.loads((first_output / "manifest.json").read_text(encoding="utf-8"))

    assert first.document_count == second.document_count == 5
    assert first.literal_citation_count == second.literal_citation_count == 10
    assert first.pending_citation_count == second.pending_citation_count == 20
    assert manifest["schema_version"] == "residenciafiscal-okf-manifest/3"
    assert manifest["scope"]["documents"] == 5
    assert manifest["scope"]["source_files"] == sorted(source_files)
    assert len(manifest["analysis_records"]) == 5
    assert len(manifest["pdf_sources"]) == 5
    assert len(manifest["documents"]) == 5
    assert _snapshot(first_output) == _snapshot(second_output)
    assert validate_okf_bundle(first_output) == ()


def test_no_publica_un_bundle_parcial_si_falta_un_pdf(tmp_path: Path) -> None:
    jsonl_path, pdf_dir, source_files = _inputs(tmp_path)
    output_dir = tmp_path / "bundle"
    (pdf_dir / source_files[0]).unlink()

    with pytest.raises(FileNotFoundError):
        build_okf_batch(
            jsonl_path=jsonl_path,
            pdf_dir=pdf_dir,
            output_dir=output_dir,
            source_files=source_files,
            threshold=85,
            page_loader=lambda _path: _pages(),
        )

    assert not output_dir.exists()


def test_rechaza_duplicados_y_un_destino_existente(tmp_path: Path) -> None:
    jsonl_path, pdf_dir, source_files = _inputs(tmp_path)
    output_dir = tmp_path / "bundle"

    with pytest.raises(ValueError, match="duplicados"):
        build_okf_batch(
            jsonl_path=jsonl_path,
            pdf_dir=pdf_dir,
            output_dir=output_dir,
            source_files=(*source_files, source_files[0]),
            threshold=85,
            page_loader=lambda _path: _pages(),
        )

    output_dir.mkdir()
    with pytest.raises(FileExistsError):
        build_okf_batch(
            jsonl_path=jsonl_path,
            pdf_dir=pdf_dir,
            output_dir=output_dir,
            source_files=source_files,
            threshold=85,
            page_loader=lambda _path: _pages(),
        )
