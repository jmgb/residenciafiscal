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


_HASH_SUFFIX_RE = re.compile(r"-([0-9a-f]{10})$")


def short_id(value: str) -> str:
    """Forma corta para vistas legibles: el sufijo hash basta como dirección.

    Los IDs sin sufijo hash (fijos, como `cita-carga-prueba`) se devuelven
    íntegros; el informe de verificación conserva siempre el ID completo.
    """

    match = _HASH_SUFFIX_RE.search(value)
    return match.group(1) if match else value
