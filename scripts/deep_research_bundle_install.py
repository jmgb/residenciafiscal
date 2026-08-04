#!/usr/bin/env python3
"""Install one verified C1 bundle and runtime on an Alfredo VPS host.

This script is intentionally stdlib-only so it can be copied to the VPS for a
single deployment. Immutable artifacts live on the host and the runtime mount
into the hardened Codex container is attested as read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
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


def runtime_release_files(sources: list[Path], schema: Path) -> list[tuple[str, Path, int]]:
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
    release_files = [(source.name, source, 0o555) for source in sources]
    release_files.append(("output.schema.json", schema, 0o444))
    return sorted(release_files)


def existing_runtime_matches(release: Path, release_files: list[tuple[str, Path, int]]) -> bool:
    if (
        not release.is_dir()
        or release.is_symlink()
        or stat.S_IMODE(release.stat().st_mode) != 0o555
    ):
        return False
    expected = {target_name: (sha256(source), mode) for target_name, source, mode in release_files}
    actual: set[str] = set()
    for path in release.iterdir():
        if path.is_symlink() or not path.is_file():
            return False
        actual.add(path.name)
        if path.name not in expected:
            return False
        expected_hash, expected_mode = expected[path.name]
        if sha256(path) != expected_hash or stat.S_IMODE(path.stat().st_mode) != expected_mode:
            return False
    return actual == set(expected)


def install_runtime(sources: list[Path], schema: Path, destination: Path) -> Path:
    """Publish an immutable host-side release and atomically select it."""
    release_files = runtime_release_files(sources, schema)
    digest = hashlib.sha256()
    for target_name, source, _mode in sorted(release_files):
        digest.update(target_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
    release_id = digest.hexdigest()
    releases = destination / "releases"
    release = releases / release_id
    releases.mkdir(parents=True, exist_ok=True)
    if release.exists():
        if not existing_runtime_matches(release, release_files):
            raise FileExistsError(f"immutable runtime release was altered: {release}")
    else:
        with tempfile.TemporaryDirectory(prefix="runtime-", dir=releases) as raw_tmp:
            temporary = Path(raw_tmp)
            for target_name, source, mode in release_files:
                target = temporary / target_name
                target.write_bytes(source.read_bytes())
                os.chmod(target, mode)
            os.chmod(temporary, 0o555)
            os.replace(temporary, release)

    temporary_link = destination / f".current-{secrets.token_hex(8)}"
    try:
        os.symlink(Path("releases") / release_id, temporary_link)
        os.replace(temporary_link, destination / "current")
    finally:
        temporary_link.unlink(missing_ok=True)
    return release


def verify_container_runtime_mount(
    container: str, host_destination: Path, container_destination: str
) -> None:
    """Fail closed unless the hardened container sees this runtime read-only."""
    result = subprocess.run(
        ["docker", "inspect", container],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        inspection = json.loads(result.stdout)
        config = inspection[0]
    except (json.JSONDecodeError, IndexError, KeyError, TypeError) as exc:
        raise RuntimeError("docker inspect returned an invalid container description") from exc
    if config.get("HostConfig", {}).get("ReadonlyRootfs") is not True:
        raise RuntimeError("Codex container root filesystem is not read-only")
    expected_source = str(host_destination.resolve())
    matching_mounts = [
        mount
        for mount in config.get("Mounts", [])
        if mount.get("Destination") == container_destination
        and str(Path(mount.get("Source", "")).resolve()) == expected_source
    ]
    if len(matching_mounts) != 1 or matching_mounts[0].get("RW") is not False:
        raise RuntimeError(
            f"Codex runtime must be mounted read-only from {expected_source} "
            f"at {container_destination}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--runtime-source", action="append", type=Path, required=True)
    parser.add_argument("--runtime-destination", type=Path)
    parser.add_argument(
        "--runtime-container-destination",
        default="/opt/residenciafiscal/deep-research/runtime",
    )
    args = parser.parse_args()
    installed = install_bundle(args.bundle.resolve(), args.root.resolve(), args.bundle_id)
    runtime_destination = (
        args.runtime_destination.resolve()
        if args.runtime_destination
        else args.root.resolve() / "runtime"
    )
    verify_container_runtime_mount(
        args.container,
        runtime_destination,
        args.runtime_container_destination,
    )
    release = install_runtime(
        [source.resolve() for source in args.runtime_source],
        args.schema.resolve(),
        runtime_destination,
    )
    print(f"installed immutable deep-research bundle: {installed}")
    print(f"installed immutable deep-research runtime: {release}")


if __name__ == "__main__":
    main()
