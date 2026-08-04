#!/usr/bin/env python3
"""Instalador del runtime del chat en el host, sin depender de un checkout.

Se ejecuta en Alfredo con la biblioteca estándar. Verifica cada hash declarado
en el manifiesto antes de escribir nada, instala la release completa y solo
entonces mueve `current` con un rename atómico. Una release a medias nunca
puede quedar activa.

El contenedor se recrea cerrado: sin credenciales de proveedor ni de Supabase,
escuchando únicamente en la dirección indicada. Abrirlo es una decisión
posterior del operador sobre su env file.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

MANIFEST_NAME = "chat-runtime-manifest.json"
SCHEMA_VERSION = "residenciafiscal-chat-runtime-artifact/1"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or name.startswith("/"):
        fail(f"ruta insegura en el artefacto: {name}")


def extract(archive: Path, destination: Path) -> dict[str, object]:
    with tarfile.open(archive, mode="r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            safe_member(member.name)
            if not member.isfile():
                fail(f"el artefacto solo puede contener ficheros: {member.name}")
        tar.extractall(destination, filter="data")
    manifest_path = destination / MANIFEST_NAME
    if not manifest_path.is_file():
        fail("el artefacto no trae manifiesto")
    manifest: dict[str, object] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        fail(f"schema del manifiesto no reconocido: {manifest.get('schema_version')}")
    return manifest


def verify(destination: Path, manifest: dict[str, object]) -> None:
    digests = manifest["sha256"]
    assert isinstance(digests, dict)
    files = manifest["files"]
    assert isinstance(files, list)
    for name in files:
        path = destination / str(name)
        if not path.is_file():
            fail(f"falta un fichero declarado: {name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != digests[str(name)]:
            fail(f"hash distinto del declarado: {name}")
    extra = {
        str(item.relative_to(destination))
        for item in destination.rglob("*")
        if item.is_file() and item.name != MANIFEST_NAME
    } - {str(name) for name in files}
    if extra:
        fail(f"ficheros no declarados en el manifiesto: {sorted(extra)[:5]}")


def harden(path: Path) -> None:
    for item in path.rglob("*"):
        item.chmod(0o555 if item.is_dir() else 0o444)
    path.chmod(0o555)


def drop(path: Path) -> None:
    """Borra una release ya endurecida.

    Sin devolver permiso de escritura a los directorios, `rmtree` no puede
    vaciarlos y reinstalar la misma release fallaba a medias: la release
    quedaba escrita pero `current` seguía apuntando a la anterior.
    """
    if not path.exists():
        return
    path.chmod(0o755)
    for item in path.rglob("*"):
        if item.is_dir():
            item.chmod(0o755)
    for item in path.rglob("*"):
        if item.is_file():
            item.chmod(0o644)
    shutil.rmtree(path)


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def main() -> int:
    if len(sys.argv) != 3:
        fail("uso: install_chat_runtime.py <artefacto.tar.gz> <dockerfile>")
    artifact = Path(sys.argv[1]).resolve()
    dockerfile = Path(sys.argv[2]).resolve()
    root = Path(os.environ.get("CHAT_RUNTIME_REMOTE_ROOT", "/opt/residenciafiscal/chat-runtime"))
    container = os.environ.get("CHAT_RUNTIME_CONTAINER", "residenciafiscal-chat")
    image = os.environ.get("CHAT_RUNTIME_IMAGE", "residenciafiscal-chat-runtime")
    bind = os.environ.get("CHAT_RUNTIME_BIND", "127.0.0.1")
    port = os.environ.get("CHAT_RUNTIME_PORT", "8021")
    memory = os.environ.get("CHAT_RUNTIME_MEMORY", "1g")
    cpus = os.environ.get("CHAT_RUNTIME_CPUS", "1.0")
    pids = os.environ.get("CHAT_RUNTIME_PIDS", "256")

    releases = root / "releases"
    run(["sudo", "mkdir", "-p", str(releases)])
    run(["sudo", "chown", f"{os.getuid()}:{os.getgid()}", str(root), str(releases)])

    with tempfile.TemporaryDirectory() as staging_name:
        staging = Path(staging_name) / "release"
        staging.mkdir()
        manifest = extract(artifact, staging)
        verify(staging, manifest)
        release_id = hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        target = releases / release_id
        declared = manifest["files"]
        assert isinstance(declared, list)
        print(f"release {release_id} · {len(declared)} ficheros verificados")
        drop(target)
        shutil.copytree(staging, target)
        harden(target)

    # El env file es del operador: si no existe, se crea cerrado y vacío de
    # secretos. Nunca se sobreescribe uno ya configurado.
    env_file = root / "chat-runtime.env"
    if not env_file.exists():
        env_file.write_text(
            "CHAT_COMPARISON_ENABLED=false\n"
            "CHAT_PROXY_HMAC_REQUIRED=false\n"
            "CHAT_RATE_LIMIT_ENABLED=false\n"
            "CHAT_RUNTIME_HASH_REQUIRED=true\n"
            "CHAT_RUNTIME_MANIFEST=/srv/chat/chat-runtime-manifest.json\n"
            "SENTRY_COMPONENT=chat-backend\n",
            encoding="utf-8",
        )
        env_file.chmod(0o600)

    current = root / "current"
    staged_link = root / f"current.{release_id}"
    if staged_link.exists() or staged_link.is_symlink():
        staged_link.unlink()
    staged_link.symlink_to(releases / release_id)
    os.replace(staged_link, current)

    run(["docker", "build", "-f", str(dockerfile), "-t", image, str(current.resolve())])

    previous = subprocess.run(
        ["docker", "ps", "-aq", "-f", f"name=^{container}$"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if previous:
        run(["docker", "rm", "-f", container])
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "--restart",
            "unless-stopped",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            memory,
            "--cpus",
            cpus,
            "--pids-limit",
            pids,
            "--env-file",
            str(env_file),
            "-p",
            f"{bind}:{port}:8000",
            image,
        ]
    )
    print(f"contenedor {container} activo en {bind}:{port} · release {release_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
