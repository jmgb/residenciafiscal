"""Validación determinista de perfiles jurídicos propuestos por un agente."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from pypdf import PdfReader

from okf_provenance import sha256_file

_EXCERPT_RE = re.compile(
    r"<!-- SOURCE_EXCERPT pdf_page_index=(\d+) id=([^ ]+) -->\n"
    r"(.*?)\n<!-- END_SOURCE_EXCERPT -->",
    re.DOTALL,
)


@dataclass(frozen=True)
class AgentProfileValidation:
    """Métricas verificadas de un perfil experimental."""

    pdf_page_count: int
    source_excerpt_count: int
    source_sha256: str


def _frontmatter(profile_path: Path, content: str) -> dict[str, object]:
    if not content.startswith("---\n"):
        raise ValueError(f"{profile_path}: frontmatter ausente")
    _, raw_frontmatter, _ = content.split("---", 2)
    parsed = yaml.safe_load(raw_frontmatter)
    if not isinstance(parsed, dict):
        raise ValueError(f"{profile_path}: frontmatter inválido")
    return cast(dict[str, object], parsed)


def _resolve_pdf(
    profile_path: Path,
    resource: str,
    repository_root: Path | None,
) -> Path:
    relative_candidate = (profile_path.parent / resource).resolve()
    if relative_candidate.is_file():
        return relative_candidate
    if repository_root is not None:
        repository_candidate = repository_root / "sentencias" / Path(resource).name
        if repository_candidate.is_file():
            return repository_candidate
    raise ValueError(f"{profile_path}: PDF no encontrado {resource}")


def _extract_blockquote(block: str, excerpt_id: str) -> str:
    lines = block.splitlines()
    if not lines or any(not line.startswith("> ") for line in lines):
        raise ValueError(f"{excerpt_id}: bloque de fuente inválido")
    return "\n".join(line[2:] for line in lines)


def validate_agent_profile(
    profile_path: Path,
    *,
    repository_root: Path | None = None,
) -> AgentProfileValidation:
    """Valida un perfil experimental antes de incorporarlo a la comparación."""

    content = profile_path.read_text(encoding="utf-8")
    frontmatter = _frontmatter(profile_path, content)
    resource = frontmatter.get("resource")
    expected_sha256 = frontmatter.get("source_sha256")
    if not isinstance(resource, str) or not isinstance(expected_sha256, str):
        raise ValueError(f"{profile_path}: procedencia incompleta")
    pdf_path = _resolve_pdf(profile_path, resource, repository_root)
    actual_sha256 = sha256_file(pdf_path)
    if actual_sha256 != expected_sha256:
        raise ValueError(f"{profile_path}: source_sha256 no coincide")

    pages = tuple(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
    matches = _EXCERPT_RE.findall(content)
    excerpt_ids = tuple(excerpt_id for _, excerpt_id, _ in matches)
    if not matches or len(excerpt_ids) != len(set(excerpt_ids)):
        raise ValueError(f"{profile_path}: extractos ausentes o IDs duplicados")
    for raw_page, excerpt_id, block in matches:
        page_index = int(raw_page)
        if page_index > len(pages):
            raise ValueError(f"{excerpt_id}: página inexistente {page_index}")
        if _extract_blockquote(block, excerpt_id) not in pages[page_index - 1]:
            raise ValueError(f"{excerpt_id}: el extracto no es literal")
    return AgentProfileValidation(
        pdf_page_count=len(pages),
        source_excerpt_count=len(matches),
        source_sha256=actual_sha256,
    )
