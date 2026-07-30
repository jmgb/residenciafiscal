"""JSON Schema versionado del índice de recuperación por cuestión."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas/residenciafiscal-retrieval-v1.schema.json"


def test_schema_versionado_coincide_con_el_modelo() -> None:
    from jurisprudence_case_retrieval_schema import render_retrieval_json_schema

    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_retrieval_json_schema()


def test_export_del_schema_es_determinista(tmp_path: Path) -> None:
    from jurisprudence_case_retrieval_schema import write_retrieval_json_schema

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    write_retrieval_json_schema(first)
    write_retrieval_json_schema(second)

    assert first.read_bytes() == second.read_bytes()
