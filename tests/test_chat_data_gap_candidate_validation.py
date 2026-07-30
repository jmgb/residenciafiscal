from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate(root: Path, quote: str) -> dict[str, object]:
    pdf = root / "sentencias" / "case.pdf"
    verbatim = root / "knowledge" / "case.pages.json"
    return {
        "schema_version": "residenciafiscal-chat-data-gap-candidate/1",
        "status": "PROPOSED_NOT_APPLIED",
        "requires_human_legal_review": True,
        "canonical_outputs_modified": False,
        "question_ids": ["DAY-05"],
        "sources": [
            {
                "judgment_id": "case",
                "source_file": "sentencias/case.pdf",
                "source_sha256": _sha256(pdf),
                "verbatim_path": "knowledge/case.pages.json",
                "verbatim_sha256": _sha256(verbatim),
                "page_index": 0,
                "quote": quote,
                "fidelity": "EXACT",
            }
        ],
        "proposed_changes": [{"target": "case", "operation": "ADD"}],
    }


def _write_sources(root: Path) -> str:
    quote = "Las ausencias esporádicas se computarán."
    pdf = root / "sentencias" / "case.pdf"
    verbatim = root / "knowledge" / "case.pages.json"
    pdf.parent.mkdir()
    verbatim.parent.mkdir()
    pdf.write_bytes(b"pdf")
    verbatim.write_text(
        json.dumps(
            {
                "document_id": "case",
                "source_file": "sentencias/case.pdf",
                "source_sha256": _sha256(pdf),
                "pages": [{"page_index": 0, "raw_page_text": f"Antes. {quote} Después."}],
            }
        ),
        encoding="utf-8",
    )
    return quote


def test_candidato_valida_citas_literales_y_hashes(tmp_path: Path) -> None:
    from chat_data_gap_candidate_validation import validate_candidate

    quote = _write_sources(tmp_path)

    result = validate_candidate(_candidate(tmp_path, quote), project_root=tmp_path)

    assert result.valid is True
    assert result.errors == ()


def test_candidato_rechaza_texto_alterado_y_hash_incorrecto(tmp_path: Path) -> None:
    from chat_data_gap_candidate_validation import validate_candidate

    quote = _write_sources(tmp_path)
    candidate = _candidate(tmp_path, quote.replace("computarán", "no computarán"))
    candidate["sources"][0]["source_sha256"] = "0" * 64  # type: ignore[index]

    result = validate_candidate(candidate, project_root=tmp_path)

    assert result.valid is False
    assert any("source_sha256" in error for error in result.errors)
    assert any("no es subcadena literal" in error for error in result.errors)


def test_candidato_debe_permanecer_fuera_del_corpus_canonico(tmp_path: Path) -> None:
    from chat_data_gap_candidate_validation import validate_candidate

    quote = _write_sources(tmp_path)
    candidate = _candidate(tmp_path, quote)
    candidate["status"] = "APPLIED"
    candidate["canonical_outputs_modified"] = True

    result = validate_candidate(candidate, project_root=tmp_path)

    assert result.valid is False
    assert any("PROPOSED_NOT_APPLIED" in error for error in result.errors)
    assert any("canonical_outputs_modified" in error for error in result.errors)
