"""Contrato del registro bilateral: qué convenio rige entre España y cada país.

Hasta ahora la relación se expresaba con un `treatyBoeId` dentro de la página de
país, que solo funciona mientras España sea la contraparte implícita, y con una
tabla corta de rangos dentro del enlazador de citas. Ninguna de las dos podía
responder a «qué convenio regía el ejercicio 2012», que es justo lo que decide
si una sentencia aplica el convenio antiguo o el nuevo.

Lo que se comprueba aquí es que el registro cubre el corpus normativo entero,
que cada contraparte resuelve a una jurisdicción del catálogo y que los periodos
no se solapan ni dejan huecos sin declarar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jurisdictions import cargar_catalogo
from treaty_relations import (
    REGISTRO_JSON,
    RegistroRelaciones,
    cargar_relaciones,
    contraparte_de,
    instrumento_vigente,
    instrumentos_de,
    render_treaty_relations_json_schema,
)

PROJECT_ROOT = Path(__file__).parents[1]
SCHEMA = PROJECT_ROOT / "schemas" / "residenciafiscal-treaty-relations-v1.schema.json"
MANIFIESTO = PROJECT_ROOT / "normativa" / "es" / "manifest.json"

GRUPOS_DE_CONVENIO_GENERAL = frozenset({"cdi", "cdi_derogado"})


@pytest.fixture(scope="module")
def convenios_del_manifiesto() -> dict[str, str]:
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    return {
        norma["id"]: norma["grupo"]
        for norma in manifiesto["normas"]
        if norma["grupo"] in GRUPOS_DE_CONVENIO_GENERAL
    }


def test_el_json_schema_versionado_esta_sincronizado() -> None:
    assert SCHEMA.read_text(encoding="utf-8") == render_treaty_relations_json_schema()


def test_el_registro_carga_con_el_contrato_estricto() -> None:
    from pydantic import ValidationError

    crudo = json.loads(REGISTRO_JSON.read_text(encoding="utf-8"))
    RegistroRelaciones.model_validate(crudo)

    crudo["relations"][0]["notas"] = "campo nuevo"
    with pytest.raises(ValidationError):
        RegistroRelaciones.model_validate(crudo)


def test_toda_contraparte_existe_en_el_catalogo_de_jurisdicciones() -> None:
    catalogo = cargar_catalogo()
    for code in cargar_relaciones():
        assert code in catalogo, code


def test_todo_instrumento_existe_en_el_corpus_normativo(convenios_del_manifiesto) -> None:
    """D2: una relación no puede apuntar a un texto que no está versionado."""
    for code, relacion in cargar_relaciones().items():
        for instrumento in relacion.instruments:
            assert instrumento.boe_id in convenios_del_manifiesto, f"{code}: {instrumento.boe_id}"


def test_el_registro_cubre_todos_los_convenios_generales(convenios_del_manifiesto) -> None:
    """Cobertura completa del Gate A: ni un convenio sin contraparte resuelta."""
    registrados = {
        instrumento.boe_id
        for relacion in cargar_relaciones().values()
        for instrumento in relacion.instruments
    }
    assert registrados == set(convenios_del_manifiesto)


def test_las_normas_reclasificadas_no_entran_en_el_registro() -> None:
    """La ley interna y los dos convenios sectoriales no son relaciones CDI."""
    from descargar_normativa import RECLASIFICACION

    registrados = {
        instrumento.boe_id
        for relacion in cargar_relaciones().values()
        for instrumento in relacion.instruments
    }
    assert not registrados & set(RECLASIFICACION)


def test_cada_contraparte_tiene_exactamente_un_instrumento_vigente() -> None:
    for code, relacion in cargar_relaciones().items():
        vigentes = [i for i in relacion.instruments if i.status == "current"]
        assert len(vigentes) == 1, f"{code}: {len(vigentes)} instrumentos «current»"


def test_los_instrumentos_sustituidos_declaran_su_sucesor() -> None:
    for code, relacion in cargar_relaciones().items():
        for instrumento in relacion.instruments:
            if instrumento.status != "superseded":
                continue
            assert instrumento.replaced_by, f"{code}: {instrumento.boe_id} sin `replaced_by`"
            sucesores = {i.boe_id for i in relacion.instruments}
            assert instrumento.replaced_by in sucesores


def test_los_periodos_no_se_solapan_ni_dejan_huecos() -> None:
    """Un hueco silencioso deja un ejercicio sin convenio aplicable."""
    for code, relacion in cargar_relaciones().items():
        anterior = None
        for instrumento in relacion.instruments:
            if anterior is not None:
                assert anterior.effective_to_tax_year is not None, code
                assert instrumento.effective_from_tax_year is not None, code
                assert instrumento.effective_from_tax_year == anterior.effective_to_tax_year + 1, (
                    f"{code}: hueco o solape entre {anterior.boe_id} y {instrumento.boe_id}"
                )
            anterior = instrumento


@pytest.mark.parametrize(
    ("code", "ejercicio", "esperado"),
    [
        ("gb", 2013, "BOE-A-1976-23347"),
        ("gb", 2014, "BOE-A-2014-5171"),
        ("ar", 2012, "BOE-A-1994-20084"),
        ("ar", 2013, "BOE-A-2014-373"),
        # El convenio de 2018 surte efecto para los ejercicios que comienzan
        # desde el 1 de enero del año siguiente a su entrada en vigor (1-5-2021).
        ("jp", 2021, "BOE-A-1974-1930"),
        ("jp", 2022, "BOE-A-2021-2977"),
        ("ro", 2021, "BOE-A-1980-21211"),
        ("ro", 2022, "BOE-A-2020-15493"),
        ("cn", 2021, "BOE-A-1992-14734"),
        ("cn", 2022, "BOE-A-2021-4911"),
        ("fr", 2010, "BOE-A-1997-12729"),
    ],
)
def test_resuelve_el_convenio_que_rige_cada_ejercicio(
    code: str, ejercicio: int, esperado: str
) -> None:
    instrumento = instrumento_vigente(code, ejercicio)
    assert instrumento is not None
    assert instrumento.boe_id == esperado


def test_japon_rumania_y_china_modelan_la_sucesion_que_el_boe_no_marca() -> None:
    """§2.2: sus dos convenios figuran con `derogada: false` en el consolidado.

    El estado jurídico vive aquí, no en el `grupo` del manifiesto, que describe
    cómo se obtiene la fuente del BOE y no si el convenio sigue aplicándose.
    """
    for code in ("jp", "ro", "cn"):
        instrumentos = instrumentos_de(code)
        assert len(instrumentos) == 2, code
        assert [i.status for i in instrumentos] == ["superseded", "current"]


def test_la_contraparte_de_un_convenio_se_resuelve_sin_mirar_su_titulo() -> None:
    """Deducir el país con una regex sobre el título publicaría otro Estado."""
    assert contraparte_de("BOE-A-1990-30940") == "us"
    assert contraparte_de("BOE-A-1967-3470") == "ch"
    assert contraparte_de("BOE-A-1981-15642") == "cshh"
    assert contraparte_de("BOE-A-1996-28330") is None


def test_los_convenios_de_estados_extintos_conservan_su_contraparte_historica() -> None:
    """No se declara sucesión: quién hereda el convenio es criterio jurídico."""
    for code in ("cshh", "suhh"):
        assert len(instrumentos_de(code)) == 1
        assert instrumentos_de(code)[0].status == "current"


def test_el_treaty_boe_id_de_cada_ruta_coincide_con_el_instrumento_vigente() -> None:
    """El dato del frontend y el registro no pueden discrepar."""
    rutas = json.loads(
        (PROJECT_ROOT / "frontend" / "src" / "data" / "countryRoutes.json").read_text("utf-8")
    )
    for ruta in rutas:
        declarado = ruta.get("treatyBoeId")
        if declarado is None:
            continue
        vigente = instrumento_vigente(ruta["code"])
        assert vigente is not None, ruta["code"]
        assert vigente.boe_id == declarado, ruta["code"]
