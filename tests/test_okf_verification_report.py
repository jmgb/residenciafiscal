"""La trazabilidad de citas vive en un sidecar JSON; el Markdown queda ligero."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from test_okf_normalization import _raw_judgment

from citation_verification import verify_citation_pages
from okf_bundle import build_okf_bundle
from okf_models import OkfProvenance
from okf_normalization import normalize_judgment
from okf_rendering import render_judgment_markdown
from okf_stable_ids import short_id
from okf_validation import validate_okf_bundle
from okf_verification_report import build_verification_report

sys.path.insert(0, str(Path(__file__).parent))


def _provenance() -> OkfProvenance:
    return OkfProvenance(
        pdf_resource="../../../sentencias/SAN_1071_2025.pdf",
        pdf_sha256="a" * 64,
        pdf_size_bytes=1000,
        pdf_page_count=4,
        analysis_source="../sources/san-1071-2025.analysis.json",
        analysis_sha256="b" * 64,
        generated_by="residenciafiscal-pipeline/0.1.0",
    )


def _judgment_and_verifications():
    judgment = normalize_judgment(_raw_judgment())
    pages = (
        "Portada",
        "Antecedentes",
        "suministros de agua y electricidad",
        "vivienda donde se alega residir",
        "la Administración ha acreditado la residencia",
    )
    verifications = tuple(
        verify_citation_pages(
            quote=citation.texto,
            declared_page=citation.pagina,
            pages=pages,
            threshold=85,
        )
        for citation in judgment.citas
    )
    return judgment, verifications


class TestShortId:
    def test_reduce_un_id_estable_a_su_sufijo_hash(self) -> None:
        assert short_id("prueba-aeat-suministros-vivienda-1ede578fd8") == "1ede578fd8"

    def test_conserva_ids_sin_sufijo_hash(self) -> None:
        assert short_id("cita-carga-prueba") == "cita-carga-prueba"
        assert short_id("residencia-fiscal") == "residencia-fiscal"


class TestVerificationReport:
    def test_una_fila_por_cita_con_ids_completos(self) -> None:
        judgment, verifications = _judgment_and_verifications()

        report = build_verification_report(judgment, verifications, threshold=85)

        assert report["schema_version"] == "residenciafiscal-okf-verification/1"
        assert report["source_file"] == "SAN_1071_2025.pdf"
        assert report["threshold"] == 85
        citations = report["citas"]
        assert isinstance(citations, list)
        assert len(citations) == len(judgment.citas)
        first = citations[0]
        assert isinstance(first, dict)
        assert first["id"] == judgment.citas[0].id
        assert first["owner_id"] == judgment.citas[0].owner_id
        assert first["source_field"] == judgment.citas[0].source_field
        assert {"evidence_status", "literal_fidelity", "score", "publishable_literal"} <= set(first)


class TestMarkdownLigero:
    def test_sin_tabla_de_trazabilidad_y_con_enlace_al_informe(self) -> None:
        judgment, verifications = _judgment_and_verifications()

        document = render_judgment_markdown(
            judgment,
            _provenance(),
            verifications,
            threshold=85,
            verification_report_resource="../reports/san-1071-2025.verification.json",
        )

        assert "# Trazabilidad de citas" not in document
        assert "(../reports/san-1071-2025.verification.json)" in document

    def test_las_tablas_imprimen_ids_cortos(self) -> None:
        judgment, verifications = _judgment_and_verifications()

        document = render_judgment_markdown(
            judgment,
            _provenance(),
            verifications,
            threshold=85,
        )

        for evidence in judgment.pruebas_aeat:
            assert evidence.id not in document
            assert f"`{short_id(evidence.id)}`" in document
        assert not re.search(r"`(?:cita|prueba)-[a-z0-9-]{20,}`", document)

    def test_deduplica_citas_literales_repetidas(self) -> None:
        judgment, verifications = _judgment_and_verifications()
        repeated = "suministros de agua y electricidad"
        literal_excerpts = [
            " […] ".join(verification.source_fragments_verbatim)
            for verification in verifications
            if verification.publishable_literal
        ]
        assert literal_excerpts.count(repeated) >= 2, "el fixture debe traer el texto duplicado"

        document = render_judgment_markdown(
            judgment,
            _provenance(),
            verifications,
            threshold=85,
        )

        assert document.count(f"> {repeated}") == 1


class TestBundleConInforme:
    def test_el_bundle_escribe_y_valida_el_informe_sidecar(self, tmp_path: Path) -> None:
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
            "suministros de agua y electricidad",
            "vivienda donde se alega residir",
        )

        result = build_okf_bundle(
            jsonl_path=jsonl_path,
            pdf_dir=pdf_dir,
            output_dir=output_dir,
            source_file="SAN_1071_2025.pdf",
            threshold=85,
            page_loader=lambda _path: pages,
        )

        report_path = output_dir / "reports" / "san-1071-2025.verification.json"
        assert report_path.is_file()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert len(report["citas"]) == 6
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        assert manifest["schema_version"] == "residenciafiscal-okf-manifest/2"
        reference = manifest["documents"][0]["verification_report"]
        assert reference["path"] == "reports/san-1071-2025.verification.json"
        assert validate_okf_bundle(output_dir) == ()

        report_path.write_text(
            report_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        assert any("informe de verificación" in issue for issue in validate_okf_bundle(output_dir))
