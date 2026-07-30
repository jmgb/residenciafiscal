from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ALLOWED_FILES = (
    "CHAT_STRATEGY_F03_BLIND_REVIEW.md",
    "CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md",
    "CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md",
    "CHAT_STRATEGY_F03_RUBRIC.md",
)


def _write_sources(root: Path) -> Path:
    source_dir = root / "docs" / "experiments"
    source_dir.mkdir(parents=True)
    for name in ALLOWED_FILES:
        (source_dir / name).write_text(f"# {name}\n", encoding="utf-8")
    (source_dir / "CHAT_STRATEGY_F03_REVEAL_KEY.json").write_text("secret")
    (source_dir / "CHAT_STRATEGY_F03_BUILD.json").write_text("secret")
    (source_dir / "CHAT_STRATEGY_F02_RESULTS.md").write_text("secret")
    return source_dir


def test_bundle_contiene_solo_material_ciego_y_manifest_verificable(tmp_path: Path) -> None:
    from chat_legal_review_bundle import build_legal_review_bundle

    source_dir = _write_sources(tmp_path)
    output = tmp_path / "bundle.zip"

    manifest = build_legal_review_bundle(source_dir=source_dir, output=output)

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == [*ALLOWED_FILES, "MANIFEST.json"]
        archived_manifest = json.loads(archive.read("MANIFEST.json"))
        for name in ALLOWED_FILES:
            assert (
                hashlib.sha256(archive.read(name)).hexdigest() == archived_manifest["files"][name]
            )
    assert manifest == archived_manifest
    assert manifest["schema_version"] == "residenciafiscal-chat-f03-legal-bundle/1"
    serialized_manifest = json.dumps(manifest).lower()
    assert "x_strategy" not in serialized_manifest
    assert "y_strategy" not in serialized_manifest
    assert "current_structured" not in serialized_manifest
    assert "gemini_file_search" not in serialized_manifest


def test_bundle_es_determinista(tmp_path: Path) -> None:
    from chat_legal_review_bundle import build_legal_review_bundle

    source_dir = _write_sources(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    build_legal_review_bundle(source_dir=source_dir, output=first)
    build_legal_review_bundle(source_dir=source_dir, output=second)

    assert first.read_bytes() == second.read_bytes()


def test_bundle_falla_si_falta_un_documento_permitido(tmp_path: Path) -> None:
    import pytest

    from chat_legal_review_bundle import build_legal_review_bundle

    source_dir = _write_sources(tmp_path)
    (source_dir / ALLOWED_FILES[0]).unlink()

    with pytest.raises(FileNotFoundError, match=ALLOWED_FILES[0]):
        build_legal_review_bundle(source_dir=source_dir, output=tmp_path / "bundle.zip")
