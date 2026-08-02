"""El catálogo de jurisdicciones es la única clave de cruce entre capas.

Hasta ahora cada consumidor guardaba su propia copia del nombre de un país:
`countryRoutes.json` para la web, `normativaFichas.json` para las fichas de
precepto y una tabla en `normativa_citas.py` para las sentencias. Tres copias
editables del mismo hecho divergen en silencio, y un país equivocado publica el
derecho de otro Estado con el nombre correcto encima.

Este módulo fija el contrato del catálogo: códigos estándar, slugs con la
política de URL vigente y una resolución de grafías que no adivina.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jurisdictions import (
    CATALOGO_JSON,
    Jurisdiccion,
    cargar_catalogo,
    path_de,
    render_jurisdictions_json_schema,
    resolver,
)

PROJECT_ROOT = Path(__file__).parents[1]
SCHEMA = PROJECT_ROOT / "schemas" / "residenciafiscal-jurisdictions-v1.schema.json"
COUNTRY_ROUTES = PROJECT_ROOT / "frontend" / "src" / "data" / "countryRoutes.json"
NORMATIVA_FICHAS = PROJECT_ROOT / "frontend" / "src" / "data" / "normativaFichas.json"


@pytest.fixture(scope="module")
def catalogo() -> dict[str, Jurisdiccion]:
    return cargar_catalogo()


def test_el_json_schema_versionado_esta_sincronizado() -> None:
    """El schema se genera del modelo, como el del caso v3: nunca a mano."""
    assert SCHEMA.read_text(encoding="utf-8") == render_jurisdictions_json_schema()


def test_el_catalogo_carga_con_el_contrato_estricto() -> None:
    """`extra="forbid"`: un campo nuevo no entra sin pasar por el modelo."""
    from pydantic import ValidationError

    from jurisdictions import CatalogoJurisdicciones

    crudo = json.loads(CATALOGO_JSON.read_text(encoding="utf-8"))
    CatalogoJurisdicciones.model_validate(crudo)

    crudo["jurisdictions"][0]["moneda"] = "EUR"
    with pytest.raises(ValidationError):
        CatalogoJurisdicciones.model_validate(crudo)


def test_los_codigos_son_unicos_y_del_tipo_que_declaran(catalogo) -> None:
    """Un alfa-2 inventado para un Estado extinto sería una clave falsa.

    ISO 3166-3 existe justamente para Checoslovaquia y la URSS; usarlo es
    explícito y comprobable, y el `code_type` impide confundir los dos espacios
    de códigos al cruzar con `normativa/<iso>/`, que es siempre alfa-2.
    """
    assert len(catalogo) == len({j.code for j in catalogo.values()})
    for jurisdiccion in catalogo.values():
        if jurisdiccion.code_type == "iso-3166-1-alpha-2":
            assert len(jurisdiccion.code) == 2, jurisdiccion.code
        else:
            assert jurisdiccion.code_type == "iso-3166-3-alpha-4"
            assert len(jurisdiccion.code) == 4, jurisdiccion.code
        assert jurisdiccion.code == jurisdiccion.code.lower()


def test_checoslovaquia_y_la_urss_estan_como_estados_historicos(catalogo) -> None:
    """Sus convenios siguen en el corpus; el Estado firmante ya no existe."""
    for code in ("cshh", "suhh"):
        assert catalogo[code].code_type == "iso-3166-3-alpha-4"


def test_los_slugs_cumplen_la_politica_de_url_y_son_unicos(catalogo) -> None:
    """ASCII, minúsculas y guion medio: `/estados-unidos`, nunca `/España`."""
    slugs = [j.slug for j in catalogo.values()]
    assert len(slugs) == len(set(slugs))
    for slug in slugs:
        assert slug.isascii(), slug
        assert slug == slug.lower(), slug
        assert "_" not in slug and " " not in slug, slug


def test_path_de_es_la_unica_construccion_de_ruta(catalogo) -> None:
    assert path_de("es") == "/espana"
    assert path_de("us") == "/estados-unidos"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("España", "es"),
        ("españa", "es"),
        ("ESPAÑA", "es"),
        ("Espana", "es"),
        ("Reino de España", "es"),
        ("Méjico", "mx"),
        ("Holanda", "nl"),
        ("Federación Rusa", "ru"),
        ("EEUU", "us"),
        ("Principado de Mónaco", "mc"),
    ],
)
def test_resolver_admite_grafias_declaradas(texto: str, esperado: str) -> None:
    """Los alias normalizan grafías; no deciden nada jurídico por sí solos."""
    encontrada = resolver(texto)
    assert encontrada is not None
    assert encontrada.code == esperado


def test_resolver_devuelve_none_ante_lo_desconocido() -> None:
    assert resolver("Wakanda") is None
    assert resolver("") is None


def test_resolver_no_acepta_coincidencias_parciales() -> None:
    """Buscar por subcadena convertiría «Guinea Ecuatorial» en «Guinea»."""
    assert resolver("República de Guinea Ecuatorial").code == "gq"
    assert resolver("Nueva España") is None


def test_todo_code_de_country_routes_existe_en_el_catalogo(catalogo) -> None:
    rutas = json.loads(COUNTRY_ROUTES.read_text(encoding="utf-8"))
    for ruta in rutas:
        assert ruta["code"] in catalogo, ruta["code"]


def test_el_catalogo_cubre_los_paises_de_las_fichas_de_precepto(catalogo) -> None:
    """Cobertura de las 97 fichas de CDI: ni un `boeId` sin jurisdicción."""
    fichas = json.loads(NORMATIVA_FICHAS.read_text(encoding="utf-8"))
    for boe_id, nombre in fichas.get("paises", {}).items():
        jurisdiccion = resolver(nombre)
        assert jurisdiccion is not None, f"{boe_id}: «{nombre}» no está en el catálogo"


def test_el_catalogo_no_precarga_jurisdicciones_sin_consumidor(catalogo) -> None:
    """§4.1: se añaden solo las necesarias para rutas o relaciones versionadas."""
    assert len(catalogo) < 120
