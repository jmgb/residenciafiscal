"""Hashes canónicos del corpus verbatim."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence


def sha256_utf8(text: str) -> str:
    """Calcula el hash de los bytes UTF-8 sin normalizar el texto."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_pages_bytes(pages: Sequence[object]) -> bytes:
    """Serializa registros de página de forma determinista."""

    return json.dumps(
        pages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_canonical_pages(pages: Sequence[object]) -> str:
    """Calcula el hash del array canónico y ordenado de páginas."""

    return hashlib.sha256(canonical_pages_bytes(pages)).hexdigest()
