"""El frontend consume el catálogo compartido; no guarda una copia editable.

`countryRoutes.json` mezclaba identidad de la jurisdicción, estado del corpus y
metadatos SEO, y `normativaFichas.json` repetía el nombre de los 92 países. Tres
copias del mismo hecho divergen en silencio: la página de un país podía decir
«Méjico» mientras la ficha de su convenio decía «México».

Lo que se comprueba aquí es que las proyecciones versionadas están al día y que
el dato de dominio ya no vive duplicado dentro de `frontend/`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from export_frontend_projections import render_jurisdictions, render_treaty_relations
from treaty_relations import cargar_relaciones, instrumento_vigente

PROJECT_ROOT = Path(__file__).parents[1]
DATOS = PROJECT_ROOT / "frontend" / "src" / "data"
JURISDICTIONS = DATOS / "jurisdictions.json"
TREATY_RELATIONS = DATOS / "treatyRelations.json"
COUNTRY_ROUTES = DATOS / "countryRoutes.json"
NORMATIVA_FICHAS = DATOS / "normativaFichas.json"


def test_las_proyecciones_versionadas_estan_sincronizadas() -> None:
    """Gate A: regenerar dos veces produce un diff vacío."""
    assert JURISDICTIONS.read_text(encoding="utf-8") == render_jurisdictions()
    assert TREATY_RELATIONS.read_text(encoding="utf-8") == render_treaty_relations()


def test_country_routes_ya_no_guarda_el_nombre_ni_el_convenio() -> None:
    """Identidad y relación bilateral son dato de dominio, no configuración web."""
    rutas = json.loads(COUNTRY_ROUTES.read_text(encoding="utf-8"))
    for ruta in rutas:
        assert "name" not in ruta, ruta["code"]
        assert "treatyBoeId" not in ruta, ruta["code"]


def test_country_routes_conserva_lo_que_si_es_decision_de_producto() -> None:
    """`indexable`, `corpusStatus` y los metadatos SEO no se tocan."""
    rutas = json.loads(COUNTRY_ROUTES.read_text(encoding="utf-8"))
    assert len(rutas) == 34
    for ruta in rutas:
        assert set(ruta) == {
            "code",
            "path",
            "corpusStatus",
            "legalReferences",
            "title",
            "description",
            "indexable",
            "sitemap",
        }, ruta["code"]


def test_las_fichas_de_precepto_ya_no_repiten_el_nombre_de_los_paises() -> None:
    fichas = json.loads(NORMATIVA_FICHAS.read_text(encoding="utf-8"))
    assert "paises" not in fichas
    assert "normas" in fichas


def test_la_ruta_de_cada_pais_coincide_con_el_slug_del_catalogo() -> None:
    """Cambiar un slug del catálogo cambiaría 34 URLs ya indexadas."""
    catalogo = json.loads(JURISDICTIONS.read_text(encoding="utf-8"))["jurisdictions"]
    rutas = json.loads(COUNTRY_ROUTES.read_text(encoding="utf-8"))
    for ruta in rutas:
        assert ruta["path"] == f"/{catalogo[ruta['code']]['slug']}", ruta["code"]


def test_la_proyeccion_bilateral_resuelve_el_convenio_de_cada_pais() -> None:
    datos = json.loads(TREATY_RELATIONS.read_text(encoding="utf-8"))
    for code, instrumentos in datos["byCounterpart"].items():
        vigentes = [i for i in instrumentos if i["status"] == "current"]
        assert len(vigentes) == 1, code
        esperado = instrumento_vigente(code)
        assert esperado is not None
        assert vigentes[0]["boeId"] == esperado.boe_id


def test_el_indice_inverso_cubre_todos_los_instrumentos() -> None:
    datos = json.loads(TREATY_RELATIONS.read_text(encoding="utf-8"))
    esperados = {
        instrumento.boe_id
        for relacion in cargar_relaciones().values()
        for instrumento in relacion.instruments
    }
    assert set(datos["byBoeId"]) == esperados


@pytest.mark.parametrize("fichero", [JURISDICTIONS, TREATY_RELATIONS])
def test_cada_proyeccion_avisa_de_que_es_generada(fichero: Path) -> None:
    datos = json.loads(fichero.read_text(encoding="utf-8"))
    assert "No editar a mano" in datos["$comment"]
