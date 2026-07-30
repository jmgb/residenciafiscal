"""Construye el ZIP ciego y reproducible para la revisión jurídica F0.3."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path

ALLOWED_FILES = (
    "CHAT_STRATEGY_F03_BLIND_REVIEW.md",
    "CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md",
    "CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md",
    "CHAT_STRATEGY_F03_RUBRIC.md",
)
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _manifest_bytes(manifest: Mapping[str, object]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def build_legal_review_bundle(*, source_dir: Path, output: Path) -> dict[str, object]:
    contents: dict[str, bytes] = {}
    for name in ALLOWED_FILES:
        path = source_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Falta el documento permitido: {name}")
        contents[name] = path.read_bytes()

    manifest: dict[str, object] = {
        "schema_version": "residenciafiscal-chat-f03-legal-bundle/1",
        "blind": True,
        "files": {name: _sha256(contents[name]) for name in ALLOWED_FILES},
    }
    contents["MANIFEST.json"] = _manifest_bytes(manifest)

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, mode="w") as archive:
        for name in (*ALLOWED_FILES, "MANIFEST.json"):
            archive.writestr(_zip_info(name), contents[name])
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    source_dir = args.project_root / "docs" / "experiments"
    build_legal_review_bundle(source_dir=source_dir, output=args.output)
    print(f"Paquete jurídico ciego creado: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
