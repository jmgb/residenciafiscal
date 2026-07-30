"""Los perfiles de experto se publican en dos sitios: aquí se atan.

`frontend/src/lib/contribution.ts` es la fuente —de ahí los leen `/colaborar` y
las páginas de país— y `CONTRIBUTING.md` los repite en una tabla, porque quien
llega por GitHub no ve la web. Dos copias del mismo texto divergen en el primer
cambio de copy, y una tabla desfasada invita a perfiles que ya no pedimos.

Limitación conocida del gate: `ci.yml` ignora los `*.md` de la raíz, así que
editar solo `CONTRIBUTING.md` no dispara este test en CI. Sí lo dispara cualquier
cambio en `contribution.ts`, que es la dirección que importa —el copy se toca en
el código y el documento se queda atrás—, y `make fast-check` lo cubre en local.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
CONTRIBUTION_TS = PROJECT_ROOT / "frontend" / "src" / "lib" / "contribution.ts"
CONTRIBUTING_MD = PROJECT_ROOT / "CONTRIBUTING.md"

# `title: 'Abogados y asesores fiscales',` dentro de EXPERT_PROFILES.
TITULO_PERFIL = re.compile(r"^\s*title:\s*'(?P<titulo>[^']+)',\s*$", re.MULTILINE)


def titulos_de_perfil() -> list[str]:
    return [m.group("titulo") for m in TITULO_PERFIL.finditer(CONTRIBUTION_TS.read_text("utf-8"))]


def test_la_fuente_declara_los_perfiles_esperados() -> None:
    """Si este test se cae, el resto no dice nada: se comprueba el propio parseo."""
    titulos = titulos_de_perfil()

    assert len(titulos) == 6, titulos
    assert titulos[0] == "Abogados y asesores fiscales"


def test_contributing_repite_los_mismos_perfiles_que_el_codigo() -> None:
    # Se comparan los títulos y no las descripciones: el detalle se redacta
    # distinto en una tabla de Markdown y en una tarjeta de la web, y exigir el
    # mismo texto ahí convertiría el test en un freno al copy.
    documento = CONTRIBUTING_MD.read_text("utf-8").replace("**", "")

    faltan = [titulo for titulo in titulos_de_perfil() if titulo not in documento]

    assert not faltan, (
        "CONTRIBUTING.md no menciona estos perfiles de contribution.ts: "
        f"{faltan}. Actualiza la tabla de «Quién puede colaborar»."
    )
