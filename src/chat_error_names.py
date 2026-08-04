"""Saneado del nombre de clase de un error antes de observarlo.

El mensaje de una excepción de proveedor puede traer el prompt incrustado, así
que nunca sale del proceso. Solo viaja el nombre de la clase, y solo si encaja
en el mismo patrón que aplica el runtime vigente.
"""

from __future__ import annotations

import re

_SAFE_ERROR_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}")


def safe_error_name(error: BaseException) -> str:
    name = type(error).__name__
    return name if _SAFE_ERROR_NAME.fullmatch(name) else "UnknownError"
