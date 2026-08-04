"""Construcción y verificación del artefacto reproducible del runtime del chat."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "residenciafiscal-chat-runtime-artifact/1"
MANIFEST_NAME = "chat-runtime-manifest.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _runtime_paths(project_root: Path) -> list[Path]:
    candidates: list[Path] = []
    source_root = project_root / "src"
    if source_root.is_dir():
        candidates.extend(
            path
            for path in source_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    for path in (
        project_root / "pyproject.toml",
        project_root / "uv.lock",
        project_root / "knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json",
        project_root / "output/file-search/rollout-106-store.json",
    ):
        if path.is_file():
            candidates.append(path)
    verbatim_root = project_root / "knowledge/jurisprudencia-v3/verbatim"
    if verbatim_root.is_dir():
        candidates.extend(path for path in verbatim_root.glob("*.pages.json") if path.is_file())
    return sorted(set(candidates))


def _archive_name(project_root: Path, path: Path) -> str:
    relative = path.relative_to(project_root).as_posix()
    _validate_archive_name(relative)
    return relative


def _validate_archive_name(name: str) -> None:
    path = PurePosixPath(name)
    allowed = (
        name.startswith("src/")
        or name in {"pyproject.toml", "uv.lock"}
        or name == "output/file-search/rollout-106-store.json"
        or name.startswith("knowledge/jurisprudencia-v3/retrieval/")
        or name.startswith("knowledge/jurisprudencia-v3/verbatim/")
    )
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or not allowed
        or name.endswith(".pdf")
        or any(
            part == ".env"
            or part.startswith(".env.")
            or part in {".git", "frontend", "credentials", "sentencias"}
            for part in path.parts
        )
    ):
        raise ValueError(f"ruta fuera de la frontera del runtime: {name}")


def _manifest(project_root: Path, paths: list[Path], version: str) -> dict[str, Any]:
    names = [_archive_name(project_root, path) for path in paths]
    return {
        "schema_version": SCHEMA_VERSION,
        "release_version": version,
        "files": names,
        "sha256": {
            name: _sha256(path.read_bytes()) for name, path in zip(names, paths, strict=True)
        },
    }


def build_chat_runtime_artifact(
    project_root: Path,
    destination: Path,
    *,
    version: str = "local",
) -> dict[str, Any]:
    """Crea un tar reproducible y devuelve el manifiesto que contiene."""
    project_root = project_root.resolve()
    destination = destination.resolve()
    paths = _runtime_paths(project_root)
    if not paths:
        raise ValueError("no hay archivos de runtime para empaquetar")
    manifest = _manifest(project_root, paths, version)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        with gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in paths:
                    name = _archive_name(project_root, path)
                    data = path.read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o644
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(data))
                manifest_data = json.dumps(
                    manifest, ensure_ascii=False, sort_keys=True, indent=2
                ).encode()
                info = tarfile.TarInfo(MANIFEST_NAME)
                info.size = len(manifest_data)
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.mtime = 0
                archive.addfile(info, io.BytesIO(manifest_data))
    return manifest


def verify_artifact(artifact: Path) -> dict[str, Any]:
    """Verifica allowlist, hashes y ausencia de rutas peligrosas."""
    with tarfile.open(artifact, mode="r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or MANIFEST_NAME not in names:
            raise ValueError("artefacto con entradas duplicadas o sin manifiesto")
        if any(_invalid_archive_name(name) for name in names if name != MANIFEST_NAME):
            raise ValueError("artefacto contiene una ruta fuera de la allowlist")
        manifest_member = archive.extractfile(MANIFEST_NAME)
        if manifest_member is None:
            raise ValueError("manifiesto ilegible")
        manifest = json.loads(manifest_member.read())
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("versión de manifiesto no compatible")
        expected_files = manifest.get("files")
        hashes = manifest.get("sha256")
        if not isinstance(expected_files, list) or not isinstance(hashes, dict):
            raise ValueError("manifiesto incompleto")
        if set(expected_files) != set(names) - {MANIFEST_NAME}:
            raise ValueError("entradas del artefacto no coinciden con el manifiesto")
        for name in expected_files:
            member = archive.extractfile(name)
            if member is None or _sha256(member.read()) != hashes.get(name):
                raise ValueError(f"hash inválido en {name}")
        return manifest


def _invalid_archive_name(name: str) -> bool:
    try:
        _validate_archive_name(name)
    except ValueError:
        return True
    return False


def verify_runtime_directory(root: Path, manifest_path: Path) -> dict[str, Any]:
    """Verifica el manifiesto instalado antes de aceptar tráfico."""
    root = root.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("versión de manifiesto no compatible")
    expected_files = manifest.get("files")
    hashes = manifest.get("sha256")
    if (
        not isinstance(expected_files, list)
        or len(expected_files) != len(set(expected_files))
        or not isinstance(hashes, dict)
    ):
        raise ValueError("manifiesto incompleto")
    for name in expected_files:
        if not isinstance(name, str):
            raise ValueError("ruta de manifiesto inválida")
        _validate_archive_name(name)
        target = (root / name).resolve()
        if root not in target.parents or not target.is_file():
            raise ValueError(f"falta un archivo del runtime: {name}")
        if _sha256(target.read_bytes()) != hashes.get(name):
            raise ValueError(f"hash inválido en {name}")
    return manifest


def install_chat_runtime_release(
    artifact: Path,
    releases_root: Path,
    current_link: Path,
    *,
    version: str,
) -> Path:
    """Instala una release y cambia el enlace activo con un rename atómico."""
    manifest = verify_artifact(artifact)
    if manifest.get("release_version") != version:
        raise ValueError("la versión solicitada no coincide con el artefacto")
    releases_root.mkdir(parents=True, exist_ok=True)
    release = releases_root / version
    if release.exists():
        raise FileExistsError(release)
    temporary = Path(tempfile.mkdtemp(prefix=f".{version}-", dir=releases_root))
    try:
        with tarfile.open(artifact, mode="r:gz") as archive:
            archive.extractall(temporary, filter="data")
        os.replace(temporary, release)
        link_tmp = current_link.with_name(f".{current_link.name}-{version}.tmp")
        if link_tmp.exists() or link_tmp.is_symlink():
            link_tmp.unlink()
        link_tmp.symlink_to(release, target_is_directory=True)
        os.replace(link_tmp, current_link)
        return release
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--version", default="local")
    args = parser.parse_args()
    manifest = build_chat_runtime_artifact(
        args.project_root, args.destination, version=args.version
    )
    print(
        f"artefacto OK: {args.destination} · release={manifest['release_version']} "
        f"· archivos={len(manifest['files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
