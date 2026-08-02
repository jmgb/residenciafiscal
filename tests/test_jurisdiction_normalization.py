"""`judgment.countries` es texto libre y hay que resolverlo sin adivinar.

En los 106 casos conviven `Mónaco` y `Principado de Mónaco`, `España-Colombia`,
`España - Emiratos Árabes Unidos`, `JAPÓN` y `Reino Unido (Londres); Suiza
(desde septiembre 2007)`. Cualquier cruce país ↔ sentencia construido sobre ese
campo sin normalizar produce enlaces falsos.

Lo que este módulo garantiza es que **todo** valor del corpus resuelve y que lo
que no resuelve falla ruidosamente, en vez de desaparecer.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from jurisdiction_normalization import (
    GRAFIAS_CORPUS,
    GrafiaDesconocida,
    normalizar_grafia_de_pais,
    normalizar_paises,
)

PROJECT_ROOT = Path(__file__).parents[1]
CASOS = sorted(glob.glob(str(PROJECT_ROOT / "knowledge/jurisprudencia-v3/cases/*.case.json")))


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("España", ("es",)),
        ("JAPÓN", ("jp",)),
        ("Japón (Tokio)", ("jp",)),
        ("Principado de Mónaco", ("mc",)),
        ("Países Bajos (Holanda)", ("nl",)),
        ("España-Colombia", ("es", "co")),
        ("España - Emiratos Árabes Unidos", ("es", "ae")),
        ("Israel;Brasil", ("il", "br")),
        ("Tailandia;Dinamarca", ("th", "dk")),
        ("EEUU; Marruecos", ("us", "ma")),
        ("Bélgica y Dinamarca", ("be", "dk")),
        ("Alemania (principal); Reino Unido (subsidiario)", ("de", "gb")),
        ("Reino Unido (CDI 1975; referido también CDI 2013)", ("gb",)),
        ("Reino Unido (Londres); Suiza (desde septiembre 2007)", ("gb", "ch")),
        ("Irán (Teherán) y Chile (Santiago de Chile)", ("ir", "cl")),
        ("República de Guinea Ecuatorial", ("gq",)),
        ("Federación Rusa", ("ru",)),
        ("Méjico", ("mx",)),
    ],
)
def test_normaliza_las_grafias_reales_del_corpus(texto: str, esperado: tuple[str, ...]) -> None:
    assert normalizar_grafia_de_pais(texto) == esperado


def test_un_nombre_compuesto_no_se_parte_por_su_conjuncion() -> None:
    """«Bosnia y Herzegovina» es un país, no dos: la cadena entera va primero."""
    assert normalizar_grafia_de_pais("Bosnia y Herzegovina") == ("ba",)
    assert normalizar_grafia_de_pais("Trinidad y Tobago") == ("tt",)


def test_una_grafia_desconocida_falla_en_vez_de_desaparecer() -> None:
    """Descartar en silencio lo no reconocido deja el corpus incompleto sin aviso."""
    with pytest.raises(GrafiaDesconocida, match="Wakanda"):
        normalizar_grafia_de_pais("Wakanda")


def test_el_orden_de_aparicion_se_conserva_y_no_hay_repetidos() -> None:
    assert normalizar_grafia_de_pais("Suiza; España; Suiza") == ("ch", "es")


def test_todos_los_valores_del_corpus_resuelven() -> None:
    """Gate A: ningún valor de `countries` puede quedar desconocido."""
    assert CASOS, "no se han encontrado los casos v3"
    for ruta in CASOS:
        caso = json.loads(Path(ruta).read_text(encoding="utf-8"))
        codigos = normalizar_paises(caso["judgment"]["countries"])
        assert codigos, caso["judgment"]["judgment_id"]


def test_toda_sentencia_del_corpus_incluye_espana() -> None:
    """Comprobación de cordura: son 106 sentencias de tribunales españoles."""
    for ruta in CASOS:
        caso = json.loads(Path(ruta).read_text(encoding="utf-8"))
        assert "es" in normalizar_paises(caso["judgment"]["countries"])


def test_cada_grafia_curada_hace_falta_de_verdad() -> None:
    """Una excepción que el motor ya resuelve es una tabla muerta que engaña."""
    for grafia in GRAFIAS_CORPUS:
        with pytest.raises(GrafiaDesconocida):
            normalizar_grafia_de_pais(grafia, usar_grafias_curadas=False)
