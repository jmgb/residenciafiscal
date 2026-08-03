from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
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


def test_instalador_publica_schema_y_runtime_en_el_host_como_release_atomica(tmp_path):
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
    destination = tmp_path / "installed-runtime"
    release = installer.install_runtime(
        [corpus, server, runtime, verifier],
        schema,
        destination,
    )

    assert release.parent == destination / "releases"
    assert {path.name for path in release.iterdir()} == {
        "deep_research_codex_runtime.py",
        "deep_research_corpus.py",
        "deep_research_corpus_mcp.py",
        "deep_research_verifier.py",
        "output.schema.json",
    }
    assert (release / "output.schema.json").read_text(encoding="utf-8") == '{"type":"object"}\n'
    assert (destination / "current").is_symlink()
    assert (destination / "current").readlink() == Path("releases") / release.name
    assert (destination / "current").resolve() == release.resolve()


def test_reintento_del_runtime_reutiliza_la_release_inmutable(tmp_path):
    installer = load_installer()
    names = {
        "deep_research_codex_runtime.py",
        "deep_research_corpus.py",
        "deep_research_corpus_mcp.py",
        "deep_research_verifier.py",
    }
    sources = []
    for name in names:
        source = tmp_path / name
        source.write_text(f"# {name}\n", encoding="utf-8")
        sources.append(source)
    schema = tmp_path / "draft.schema.json"
    schema.write_text('{"type":"object"}\n', encoding="utf-8")
    destination = tmp_path / "installed-runtime"

    first = installer.install_runtime(sources, schema, destination)
    second = installer.install_runtime(sources, schema, destination)

    assert second == first
    assert len(list((destination / "releases").iterdir())) == 1


def test_instalador_rechaza_un_runtime_inmutable_que_se_haya_hecho_escribible(tmp_path):
    installer = load_installer()
    names = {
        "deep_research_codex_runtime.py",
        "deep_research_corpus.py",
        "deep_research_corpus_mcp.py",
        "deep_research_verifier.py",
    }
    sources = []
    for name in names:
        source = tmp_path / name
        source.write_text(f"# {name}\n", encoding="utf-8")
        sources.append(source)
    schema = tmp_path / "draft.schema.json"
    schema.write_text('{"type":"object"}\n', encoding="utf-8")
    destination = tmp_path / "installed-runtime"
    release = installer.install_runtime(sources, schema, destination)
    (release / "deep_research_corpus.py").chmod(0o644)

    try:
        installer.install_runtime(sources, schema, destination)
    except FileExistsError as exc:
        assert "immutable runtime release" in str(exc)
    else:
        raise AssertionError("an altered immutable runtime must be rejected")


def test_instalador_atestigua_el_mount_antes_de_activar_el_runtime(tmp_path, monkeypatch):
    installer = load_installer()
    calls = []
    bundle = tmp_path / "bundle.zip"
    schema = tmp_path / "schema.json"
    sources = []
    for name in (
        "deep_research_codex_runtime.py",
        "deep_research_corpus.py",
        "deep_research_corpus_mcp.py",
        "deep_research_verifier.py",
    ):
        source = tmp_path / name
        source.write_text(name, encoding="utf-8")
        sources.extend(["--runtime-source", str(source)])
    bundle.write_bytes(b"bundle")
    schema.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--bundle",
            str(bundle),
            "--root",
            str(tmp_path / "installed"),
            "--bundle-id",
            "rollout-106/2",
            "--container",
            "alfredo-codex-agent",
            "--schema",
            str(schema),
            *sources,
        ],
    )
    monkeypatch.setattr(
        installer,
        "install_bundle",
        lambda *args: calls.append("bundle") or tmp_path / "installed" / "rollout-106/2",
    )
    monkeypatch.setattr(
        installer,
        "verify_container_runtime_mount",
        lambda *args: calls.append("verify"),
    )
    monkeypatch.setattr(
        installer,
        "install_runtime",
        lambda *args: calls.append("runtime") or tmp_path / "installed" / "runtime-release",
    )

    installer.main()

    assert calls == ["bundle", "verify", "runtime"]


def test_atestacion_exige_rootfs_y_mount_del_runtime_en_solo_lectura(tmp_path, monkeypatch):
    installer = load_installer()
    destination = tmp_path / "runtime"
    destination.mkdir()
    inspection = [
        {
            "HostConfig": {"ReadonlyRootfs": True},
            "Mounts": [
                {
                    "Source": str(destination),
                    "Destination": "/opt/residenciafiscal/deep-research/runtime",
                    "RW": False,
                }
            ],
        }
    ]

    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Result", (), {"stdout": json.dumps(inspection)}
        )(),
    )

    installer.verify_container_runtime_mount(
        "alfredo-codex-agent",
        destination,
        "/opt/residenciafiscal/deep-research/runtime",
    )


def test_atestacion_rechaza_mount_escribible(tmp_path, monkeypatch):
    installer = load_installer()
    destination = tmp_path / "runtime"
    destination.mkdir()
    inspection = [
        {
            "HostConfig": {"ReadonlyRootfs": True},
            "Mounts": [
                {
                    "Source": str(destination),
                    "Destination": "/opt/residenciafiscal/deep-research/runtime",
                    "RW": True,
                }
            ],
        }
    ]
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Result", (), {"stdout": json.dumps(inspection)}
        )(),
    )

    try:
        installer.verify_container_runtime_mount(
            "alfredo-codex-agent",
            destination,
            "/opt/residenciafiscal/deep-research/runtime",
        )
    except RuntimeError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("a writable runtime mount must be rejected")
