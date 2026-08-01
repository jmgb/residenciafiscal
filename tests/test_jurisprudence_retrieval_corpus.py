"""Corpus agregado y ranking léxico reproducible de la muestra v3."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_ROOT = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval"
SCHEMA_PATH = PROJECT_ROOT / "schemas/residenciafiscal-retrieval-corpus-v1.schema.json"
SAMPLE_IDS = (
    "san-1071-2025",
    "san-1136-2016",
    "san-1210-2023",
    "san-1226-2021",
    "san-1386-2017",
)


def _index_paths() -> tuple[Path, ...]:
    return tuple(RETRIEVAL_ROOT / f"{judgment_id}.issues.json" for judgment_id in SAMPLE_IDS)


def test_agrega_las_cinco_sentencias_sin_perder_cuestiones() -> None:
    from jurisprudence_retrieval_corpus import build_retrieval_corpus

    corpus = build_retrieval_corpus(
        _index_paths(),
        sample_id="jurisprudencia-v3-piloto-5",
        project_root=PROJECT_ROOT,
    )

    assert corpus.schema_version == "residenciafiscal-retrieval-corpus/1"
    assert len(corpus.sources) == 5
    assert len(corpus.units) == 12
    assert {unit.judgment_id for unit in corpus.units} == {
        "san-1071-2025",
        "san-1136-2016",
        "san-1210-2023",
        "san-1226-2021",
        "san-1386-2017",
    }


def test_serializacion_y_ranking_son_deterministas() -> None:
    from jurisprudence_retrieval_corpus import (
        build_retrieval_corpus,
        rank_retrieval_units,
        render_retrieval_corpus,
    )

    corpus = build_retrieval_corpus(
        _index_paths(),
        sample_id="jurisprudencia-v3-piloto-5",
        project_root=PROJECT_ROOT,
    )

    assert render_retrieval_corpus(corpus) == render_retrieval_corpus(corpus)
    hits = rank_retrieval_units(
        corpus,
        "¿Influyen las sociedades y el centro de intereses económicos en España?",
        limit=5,
    )
    assert hits == rank_retrieval_units(
        corpus,
        "¿Influyen las sociedades y el centro de intereses económicos en España?",
        limit=5,
    )
    assert hits[0].judgment_id in {"san-1071-2025", "san-1210-2023"}
    assert all(hit.score >= 0 for hit in hits)


def test_schema_del_corpus_esta_versionado_y_sincronizado() -> None:
    from jurisprudence_retrieval_corpus_schema import (
        render_retrieval_corpus_json_schema,
    )

    assert SCHEMA_PATH.read_text(encoding="utf-8") == (render_retrieval_corpus_json_schema())


def test_excluye_del_indice_los_documentos_clasificados_fuera_de_alcance(
    tmp_path: Path,
) -> None:
    from jurisprudence_retrieval_corpus import build_retrieval_corpus

    source = _index_paths()[0]
    in_scope = tmp_path / "in-scope.issues.json"
    out_of_scope = tmp_path / "out-of-scope.issues.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["judgment"]["is_tax_residence_case"] = True
    in_scope.write_text(json.dumps(payload), encoding="utf-8")
    payload["judgment"]["judgment_id"] = "san-fuera-2026"
    payload["judgment"]["is_tax_residence_case"] = False
    for unit in payload["units"]:
        unit["judgment_id"] = "san-fuera-2026"
        unit["unit_id"] = f"san-fuera-2026-{unit['issue']['issue_id']}"
    out_of_scope.write_text(json.dumps(payload), encoding="utf-8")

    corpus = build_retrieval_corpus(
        (in_scope, out_of_scope),
        sample_id="corpus-con-fuera-de-alcance",
        project_root=tmp_path,
    )

    assert len(corpus.sources) == 2
    assert {unit.judgment_id for unit in corpus.units} == {
        json.loads(in_scope.read_text(encoding="utf-8"))["judgment"]["judgment_id"]
    }
