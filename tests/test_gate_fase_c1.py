"""Gate C1: el renderer jurisprudencial existe y no publica nada.

`docs/product/INTERNATIONAL_ARCHITECTURE.md` §9 lo enuncia así: «literalidad,
páginas y hashes pasan; no se filtra ningún campo fuera de la allowlist; Deploy
Preview revisable y con `X-Robots-Tag: noindex`; toda ruta `internal_preview`
devuelve 404 real en producción; accesibilidad y build frontend verificados.
Este gate no concede publicación».

La literalidad completa —897 extractos contra sus 67 PDF— vive en
`make verify-public-judgments` porque abrir los PDF cuesta unos 50 segundos.
Aquí se comprueba sobre una muestra fija, igual que hace el resto del proyecto
con sus rollouts de 1 → 5 → 106.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from export_public_judgments import cargar_casos, construir_manifiesto, verificar_literalidad
from public_judgment_projection import EstadoPublicacion, proyectar

PROJECT_ROOT = Path(__file__).parents[1]
CASOS = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "cases"
PUBLICO = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "publico"
FRONTEND = PROJECT_ROOT / "frontend"

# Muestra fija de literalidad: dos casos de la muestra de cinco de la fase C y
# tres del rollout, para cubrir estructuras ricas y mínimas.
MUESTRA_LITERALIDAD = (
    "san-1210-2023",
    "san-1386-2017",
    "san-2229-2022",
    "sts-114-2018",
    "san-1071-2025",
)


@pytest.fixture(scope="module")
def casos() -> list[dict]:
    return cargar_casos(CASOS)


def test_gate_literalidad_de_la_muestra_fija(casos: list[dict]) -> None:
    """Cada extracto publicado es una subcadena exacta de su página del PDF."""
    seleccion = [caso for caso in casos if caso["judgment"]["judgment_id"] in MUESTRA_LITERALIDAD]
    assert len(seleccion) == len(MUESTRA_LITERALIDAD)

    assert verificar_literalidad(seleccion) == []


def test_gate_las_paginas_y_los_hashes_se_propagan(casos: list[dict]) -> None:
    por_id = {caso["judgment"]["judgment_id"]: caso for caso in casos}
    for judgment_id in MUESTRA_LITERALIDAD:
        caso = por_id[judgment_id]
        proyeccion = proyectar(caso)
        assert proyeccion.judgment.source_sha256 == caso["judgment"]["source_sha256"]
        for anclaje in proyeccion.anchors:
            assert anclaje.source_sha256 == caso["judgment"]["source_sha256"]
            for fragmento in anclaje.fragments:
                assert fragmento.page_index >= 1
                assert fragmento.page_index <= proyeccion.judgment.page_count


def test_gate_no_se_filtra_ningun_campo_fuera_de_la_allowlist() -> None:
    """Lo publicado no puede traer procedencia de prompts ni notas internas."""
    prohibidos = ("prompt_sha256", "promptSha256", "run_id", "runId", "input_artifacts", "notes")
    for fichero in sorted(PUBLICO.glob("*.public.json")):
        crudo = fichero.read_text(encoding="utf-8")
        for prohibido in prohibidos:
            assert prohibido not in crudo, f"{fichero.name} filtra «{prohibido}»"


def test_gate_ninguna_ficha_alcanza_published(casos: list[dict]) -> None:
    """Este gate no concede publicación: los 67 siguen siendo borradores."""
    manifiesto = construir_manifiesto(casos)

    assert manifiesto["published"] == 0
    for entrada in manifiesto["judgments"]:
        assert entrada["publicationState"] == EstadoPublicacion.INTERNAL_PREVIEW


def test_gate_el_frontend_no_puede_ascender_un_caso() -> None:
    """Ningún flag del build decide el estado: lo trae el manifiesto con hash."""
    script = (FRONTEND / "scripts" / "build-sentencias.mjs").read_text(encoding="utf-8")

    # La variable de preview solo amplía qué se materializa, nunca cambia el
    # estado que viaja al índice.
    assert "PUBLIC_STATES = ['published']" in script
    assert "projectionSha256" in script
    assert "publicationState: entry.publicationState" in script


def test_gate_produccion_no_sirve_ninguna_ruta_de_sentencia() -> None:
    """Sin fichero ni regla, el fallback de `netlify.toml` devuelve 404 real."""
    redirects = (FRONTEND / "public" / "_redirects").read_text(encoding="utf-8")
    sitemap = (FRONTEND / "public" / "sitemap.xml").read_text(encoding="utf-8")

    assert "/espana/sentencias" not in redirects
    assert "/espana/sentencias" not in sitemap

    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    fallback = [r for r in config["redirects"] if r["from"] == "/*"]
    assert fallback and fallback[0]["status"] == 404


def test_gate_el_deploy_preview_es_revisable_y_no_indexable() -> None:
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    preview = config["context"]["deploy-preview"]

    assert preview["environment"]["SENTENCIAS_PREVIEW"] == "1"
    assert "noindex" in preview["headers"][0]["values"]["X-Robots-Tag"]


def test_gate_netlify_reconstruye_si_cambia_una_proyeccion_publica() -> None:
    """El build consume estas proyecciones aunque vivan fuera de `frontend/`."""
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))

    assert ":/knowledge/jurisprudencia-v3/publico" in config["build"]["ignore"]


def test_gate_el_indice_servido_no_lleva_borradores_en_produccion() -> None:
    """El índice versionado del build público está vacío y lo declara."""
    indice = FRONTEND / "public" / "data" / "sentencias.json"
    if not indice.exists():
        pytest.skip("el índice se genera en el prebuild; no está versionado")

    datos = json.loads(indice.read_text(encoding="utf-8"))
    assert datos["schemaVersion"] == "residenciafiscal-sentencias-index/2"
    indices = datos["jurisdictions"].values()
    if any(indice_pais["includesPreview"] for indice_pais in indices):
        pytest.skip("índice generado en modo preview")
    assert all(indice_pais["judgments"] == [] for indice_pais in indices)


def test_gate_el_enlazado_publico_no_usa_countries_en_bruto(casos: list[dict]) -> None:
    """Solo roles tipados: `mentioned_only` no llega a la proyección."""
    for caso in casos:
        if not caso["judgment"]["is_tax_residence_case"]:
            continue
        proyeccion = proyectar(caso)
        for jurisdiccion in proyeccion.jurisdictions:
            assert "mentioned_only" not in jurisdiccion.roles
            assert jurisdiccion.roles
