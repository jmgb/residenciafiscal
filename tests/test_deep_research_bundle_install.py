from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/deep_research_bundle_install.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("deep_research_bundle_install", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reintento_reutiliza_un_bundle_identico_sin_sobrescribirlo(tmp_path: Path) -> None:
    installer = load_installer()
    payload = b"evidencia"
    manifest = {
        "bundle_id": "rollout-106/2",
        "files": {"verbatim/case.pages.json": hashlib.sha256(payload).hexdigest()},
    }
    bundle = tmp_path / "bundle.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("MANIFEST.json", json.dumps(manifest))
        archive.writestr("verbatim/case.pages.json", payload)

    first = installer.install_bundle(bundle, tmp_path / "installed", "rollout-106/2")
    second = installer.install_bundle(bundle, tmp_path / "installed", "rollout-106/2")

    assert second == first
    assert (second / "verbatim/case.pages.json").read_bytes() == payload


def test_instalador_publica_schema_y_runtime_en_una_unica_release_atomica(tmp_path, monkeypatch):
    installer = load_installer()
    corpus = tmp_path / "deep_research_corpus.py"
    server = tmp_path / "deep_research_corpus_mcp.py"
    runtime = tmp_path / "deep_research_codex_runtime.py"
    verifier = tmp_path / "deep_research_verifier.py"
    schema = tmp_path / "draft.schema.json"
    corpus.write_text("# corpus\n", encoding="utf-8")
    server.write_text("# server\n", encoding="utf-8")
    runtime.write_text("# runtime\n", encoding="utf-8")
    verifier.write_text("# verifier\n", encoding="utf-8")
    schema.write_text('{"type":"object"}\n', encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        installer.subprocess, "run", lambda command, **kwargs: calls.append(command)
    )

    installer.copy_runtime(
        [corpus, server, runtime, verifier],
        schema,
        "alfredo-codex-agent",
        "/opt/residenciafiscal/deep-research/runtime",
    )

    copy_calls = [call for call in calls if call[:2] == ["docker", "cp"]]
    assert len(copy_calls) == 5
    assert all("/releases/" in call[-1] for call in copy_calls)
    copied_sources = {call[2] for call in copy_calls}
    assert copied_sources == {str(runtime), str(corpus), str(server), str(verifier), str(schema)}
    schema_copy = next(call for call in copy_calls if call[2] == str(schema))
    assert schema_copy[-1].endswith("/output.schema.json")
    assert any(
        call[:3] == ["docker", "exec", "alfredo-codex-agent"] and "ln" in call for call in calls
    )
    assert any(
        call[:3] == ["docker", "exec", "alfredo-codex-agent"] and "mv" in call for call in calls
    )
    assert not any(
        call[-1].startswith(
            "alfredo-codex-agent:/opt/residenciafiscal/deep-research/runtime/deep_research_"
        )
        for call in copy_calls
    )
