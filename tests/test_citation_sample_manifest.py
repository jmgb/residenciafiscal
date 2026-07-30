"""Pruebas del manifiesto versionado para ampliar el piloto a cinco sentencias."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from citation_sample_manifest import load_sample_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_carga_un_manifiesto_y_preserva_el_orden_de_las_sentencias(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sample.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "muestra-prueba",
                "expected_documents": 2,
                "documents": [
                    {
                        "archivo": "segunda.pdf",
                        "cubre": ["parafrasis"],
                        "motivo": "Contiene una coincidencia fuzzy conocida.",
                    },
                    {
                        "archivo": "primera.pdf",
                        "cubre": ["exacta", "pagina-desplazada"],
                        "motivo": "Combina coincidencia exacta y página incorrecta.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    manifest = load_sample_manifest(manifest_path)

    assert manifest.source_files == ("segunda.pdf", "primera.pdf")


def test_rechaza_duplicados_o_un_numero_distinto_del_declarado(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sample.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "muestra-invalida",
                "expected_documents": 2,
                "documents": [
                    {"archivo": "repetida.pdf", "cubre": ["exacta"], "motivo": "Primera."},
                    {"archivo": "repetida.pdf", "cubre": ["elipsis"], "motivo": "Duplicada."},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_sample_manifest(manifest_path)


def test_el_manifiesto_versionado_contiene_cinco_pdf_existentes() -> None:
    manifest = load_sample_manifest(
        REPOSITORY_ROOT / "sentencias" / "verificacion_citas_muestra_5.json"
    )

    assert manifest.expected_documents == 5
    assert len(manifest.source_files) == 5
    assert all(
        (REPOSITORY_ROOT / "sentencias" / source_file).is_file()
        for source_file in manifest.source_files
    )
