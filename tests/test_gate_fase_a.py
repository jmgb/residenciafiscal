"""Gate A de la arquitectura internacional, en un solo sitio y ejecutable.

`docs/product/INTERNATIONAL_ARCHITECTURE.md` §9 lo enuncia así: «schemas
válidos; cobertura completa; ninguna relación tiene periodos solapados o huecos
no declarados; ningún valor de `countries` queda desconocido; ningún rol
jurídico se infiere solo por alias; regenerar dos veces da diff vacío».

Cada criterio tiene ya su test detallado en el módulo correspondiente. Este
fichero no los repite: comprueba el gate de punta a punta, para que cerrar la
fase sea ejecutar un comando y no releer seis ficheros.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from export_frontend_projections import render_jurisdictions, render_treaty_relations
from jurisdiction_normalization import normalizar_paises
from jurisdiction_roles import ROLES_TIPADOS, derivar_roles, render_sidecar
from jurisdictions import CATALOGO_JSON, CatalogoJurisdicciones, cargar_catalogo
from treaty_relations import REGISTRO_JSON, RegistroRelaciones, cargar_relaciones

PROJECT_ROOT = Path(__file__).parents[1]
CASOS = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "cases"
SIDECARS = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "jurisdicciones"
DATOS_FRONTEND = PROJECT_ROOT / "frontend" / "src" / "data"
MANIFIESTO = PROJECT_ROOT / "normativa" / "es" / "manifest.json"


@pytest.fixture(scope="module")
def casos() -> list[dict]:
    rutas = sorted(CASOS.glob("*.case.json"))
    assert len(rutas) == 106, "el corpus canónico son 106 casos"
    return [json.loads(ruta.read_text(encoding="utf-8")) for ruta in rutas]


def test_gate_1_los_documentos_validan_contra_su_contrato() -> None:
    CatalogoJurisdicciones.model_validate_json(CATALOGO_JSON.read_text(encoding="utf-8"))
    RegistroRelaciones.model_validate_json(REGISTRO_JSON.read_text(encoding="utf-8"))


def test_gate_2_cobertura_completa_de_convenios_y_rutas() -> None:
    """Ni un convenio sin contraparte, ni una ruta sin jurisdicción."""
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    convenios = {
        norma["id"] for norma in manifiesto["normas"] if norma["grupo"] in {"cdi", "cdi_derogado"}
    }
    registrados = {
        instrumento.boe_id
        for relacion in cargar_relaciones().values()
        for instrumento in relacion.instruments
    }
    assert registrados == convenios

    catalogo = cargar_catalogo()
    rutas = json.loads((DATOS_FRONTEND / "countryRoutes.json").read_text(encoding="utf-8"))
    assert {ruta["code"] for ruta in rutas} <= set(catalogo)
    assert set(cargar_relaciones()) <= set(catalogo)


def test_gate_3_ninguna_relacion_tiene_solapes_ni_huecos() -> None:
    """El modelo lo valida al cargar; aquí se comprueba que se ejerce."""
    for code, relacion in cargar_relaciones().items():
        anterior = None
        for instrumento in relacion.instruments:
            if anterior is not None:
                assert anterior.effective_to_tax_year is not None, code
                assert instrumento.effective_from_tax_year == anterior.effective_to_tax_year + 1
            anterior = instrumento


def test_gate_4_ningun_valor_de_countries_queda_desconocido(casos: list[dict]) -> None:
    for caso in casos:
        codigos = normalizar_paises(caso["judgment"]["countries"])
        assert codigos, caso["judgment"]["judgment_id"]


def test_gate_5_ningun_rol_juridico_se_infiere_solo_por_alias(casos: list[dict]) -> None:
    for caso in casos:
        sidecar = derivar_roles(caso)
        for entrada in sidecar.jurisdictions:
            if not set(entrada.roles) & ROLES_TIPADOS:
                continue
            origenes_tipados = [
                origen for origen in entrada.derived_from if origen != "judgment.countries"
            ]
            assert origenes_tipados, f"{sidecar.judgment_id}/{entrada.code}"


def test_gate_6_regenerar_dos_veces_da_diff_vacio(casos: list[dict]) -> None:
    """Todo artefacto generado de la fase A es determinista y está al día."""
    assert render_jurisdictions() == render_jurisdictions()
    assert render_treaty_relations() == render_treaty_relations()
    assert (DATOS_FRONTEND / "jurisdictions.json").read_text("utf-8") == render_jurisdictions()
    assert (DATOS_FRONTEND / "treatyRelations.json").read_text("utf-8") == render_treaty_relations()

    for caso in casos:
        contenido = render_sidecar(caso)
        assert contenido == render_sidecar(caso)
        destino = SIDECARS / f"{caso['judgment']['judgment_id']}.roles.json"
        assert destino.read_text(encoding="utf-8") == contenido


def test_gate_extra_el_dato_de_dominio_no_vive_dentro_del_frontend() -> None:
    """§4.1: colocar el catálogo canónico en `frontend/` invertiría la dependencia."""
    rutas = json.loads((DATOS_FRONTEND / "countryRoutes.json").read_text(encoding="utf-8"))
    assert all("name" not in ruta and "treatyBoeId" not in ruta for ruta in rutas)

    fichas = json.loads((DATOS_FRONTEND / "normativaFichas.json").read_text(encoding="utf-8"))
    assert "paises" not in fichas

    for proyeccion in ("jurisdictions.json", "treatyRelations.json"):
        datos = json.loads((DATOS_FRONTEND / proyeccion).read_text(encoding="utf-8"))
        assert "No editar a mano" in datos["$comment"]
