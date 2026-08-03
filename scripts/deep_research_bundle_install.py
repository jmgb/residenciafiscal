#!/usr/bin/env python3
"""Install one verified C1 bundle into an Alfredo Codex container.

This script is intentionally stdlib-only so it can be copied to the VPS for a
single deployment. It refuses to overwrite an existing bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_target(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or "\\" in name:
        raise ValueError(f"unsafe archive path: {name}")
    target = (root / Path(*relative.parts)).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"archive path escapes destination: {name}")
    return target


def existing_bundle_matches(final: Path, manifest_bytes: bytes, files: dict[str, str]) -> bool:
    manifest_path = final / "MANIFEST.json"
    if not final.is_dir() or not manifest_path.is_file():
        return False
    if manifest_path.read_bytes() != manifest_bytes:
        return False
    actual_files: set[str] = set()
    for path in final.rglob("*"):
        if path.is_symlink():
            return False
        if not path.is_file() or path == manifest_path:
            continue
        relative = path.relative_to(final).as_posix()
        actual_files.add(relative)
        if relative not in files or sha256(path) != files[relative]:
            return False
    return actual_files == set(files)


def install_bundle(bundle: Path, destination_root: Path, expected_bundle_id: str) -> Path:
    with zipfile.ZipFile(bundle) as archive:
        try:
            manifest_bytes = archive.read("MANIFEST.json")
            manifest = json.loads(manifest_bytes)
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError("bundle has no valid MANIFEST.json") from exc
        if manifest.get("bundle_id") != expected_bundle_id:
            raise ValueError("bundle_id does not match the deployment request")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError("bundle manifest has no file hashes")

        final = safe_target(destination_root, expected_bundle_id)
        if final.exists():
            if existing_bundle_matches(final, manifest_bytes, files):
                return final
            raise FileExistsError(f"immutable bundle already exists: {final}")
        final.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="deep-research-", dir=final.parent) as raw_tmp:
            temporary = Path(raw_tmp)
            seen_files: set[str] = set()
            for info in archive.infolist():
                if info.filename == "MANIFEST.json":
                    continue
                target = safe_target(temporary, info.filename)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if info.filename not in files:
                    raise ValueError(f"unlisted file in bundle: {info.filename}")
                if info.filename in seen_files:
                    raise ValueError(f"duplicate file in bundle: {info.filename}")
                seen_files.add(info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
                if sha256(target) != files[info.filename]:
                    raise ValueError(f"hash mismatch: {info.filename}")
            if seen_files != set(files):
                missing = ", ".join(sorted(set(files) - seen_files))
                raise ValueError(f"manifest file missing from bundle: {missing}")
            (temporary / "MANIFEST.json").write_bytes(manifest_bytes)
            for path in temporary.rglob("*"):
                os.chmod(path, 0o444 if path.is_file() else 0o555)
            os.replace(temporary, final)
        os.chmod(final, 0o555)
        return final


def copy_runtime(sources: list[Path], schema: Path, container: str, destination: str) -> None:
    expected = {
        "deep_research_codex_runtime.py",
        "deep_research_corpus.py",
        "deep_research_corpus_mcp.py",
        "deep_research_verifier.py",
    }
    if {source.name for source in sources} != expected or any(
        not source.is_file() for source in sources
    ):
        raise ValueError("runtime sources must be the four allowlisted profile modules")
    if not schema.is_file():
        raise FileNotFoundError(schema)
    release_files = [(source.name, source, "0555") for source in sources]
    release_files.append(("output.schema.json", schema, "0444"))
    digest = hashlib.sha256()
    for target_name, source, _mode in sorted(release_files):
        digest.update(target_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
    release_id = digest.hexdigest()
    release = f"{destination.rstrip('/')}/releases/{release_id}"
    subprocess.run(["docker", "inspect", container], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["docker", "exec", container, "mkdir", "-p", release], check=True)
    for target_name, source, mode in sorted(release_files):
        target = f"{release}/{target_name}"
        subprocess.run(["docker", "cp", str(source), f"{container}:{target}"], check=True)
        subprocess.run(["docker", "exec", container, "chmod", mode, target], check=True)
    temporary_link = f"{destination.rstrip('/')}/.current-{secrets.token_hex(8)}"
    subprocess.run(
        ["docker", "exec", container, "ln", "-s", f"releases/{release_id}", temporary_link],
        check=True,
    )
    subprocess.run(
        [
            "docker",
            "exec",
            container,
            "mv",
            "-Tf",
            temporary_link,
            f"{destination.rstrip('/')}/current",
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--runtime-source", action="append", type=Path, required=True)
    parser.add_argument(
        "--runtime-destination",
        default="/opt/residenciafiscal/deep-research/runtime",
    )
    args = parser.parse_args()
    installed = install_bundle(args.bundle.resolve(), args.root.resolve(), args.bundle_id)
    copy_runtime(
        [source.resolve() for source in args.runtime_source],
        args.schema.resolve(),
        args.container,
        args.runtime_destination,
    )
    print(f"installed immutable deep-research bundle: {installed}")


if __name__ == "__main__":
    main()
