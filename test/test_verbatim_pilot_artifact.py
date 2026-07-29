"""Gate reproducible del verbatim piloto SAN 1210/2023."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "sentencias" / "SAN_1210_2023.pdf"
ARTIFACT_PATH = (
    PROJECT_ROOT / "knowledge" / "jurisprudencia" / "verbatim" / "san-1210-2023.pages.json"
)
SOURCE_SHA256 = "4d2f5f31cf8824a4fd9df1214c791e8009d16a250990533b64047467d8459d5d"
PAGES_SHA256 = "76a3bd4547c840d2e0f23eb2e6986c7c4c14f4eca528fe98ebd7e93d9ba658ae"


def test_artefacto_piloto_coincide_con_pdf_y_reextraccion() -> None:
    from verbatim_validation import validate_verbatim_artifact

    result = validate_verbatim_artifact(
        ARTIFACT_PATH,
        project_root=PROJECT_ROOT,
    )

    assert result.document_id == "san-1210-2023"
    assert result.page_count == 10
    assert result.status == "COMPLETE"
    assert result.source_sha256 == SOURCE_SHA256
    assert result.pages_sha256 == PAGES_SHA256


def test_build_repetido_produce_exactamente_los_bytes_versionados() -> None:
    from verbatim_artifact import render_verbatim_corpus
    from verbatim_extraction import extract_verbatim_corpus

    regenerated = extract_verbatim_corpus(
        PDF_PATH,
        document_id="san-1210-2023",
        source_file="sentencias/SAN_1210_2023.pdf",
    )

    assert ARTIFACT_PATH.read_text(encoding="utf-8") == render_verbatim_corpus(regenerated)
