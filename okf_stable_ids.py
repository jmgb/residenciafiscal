"""Identificadores estables para conceptos jurídicos derivados."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping


def slugify(value: str) -> str:
    """Convierte una etiqueta en slug sin depender de su posición en una lista."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def stable_id(
    prefix: str,
    label: str,
    identity: Mapping[str, object],
) -> str:
    """Combina una etiqueta legible y una huella canónica de su identidad."""

    serialized = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:10]
    readable = slugify(label)[:48] or "sin-etiqueta"
    return f"{prefix}-{readable}-{digest}"
