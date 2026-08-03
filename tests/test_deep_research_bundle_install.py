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
        "bundle_id": "rollout-106/1",
        "files": {"verbatim/case.pages.json": hashlib.sha256(payload).hexdigest()},
    }
    bundle = tmp_path / "bundle.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("MANIFEST.json", json.dumps(manifest))
        archive.writestr("verbatim/case.pages.json", payload)

    first = installer.install_bundle(bundle, tmp_path / "installed", "rollout-106/1")
    second = installer.install_bundle(bundle, tmp_path / "installed", "rollout-106/1")

    assert second == first
    assert (second / "verbatim/case.pages.json").read_bytes() == payload
