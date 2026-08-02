"""La proyección pública es una allowlist, no una copia con campos borrados.

La diferencia importa el día que alguien añada un campo al schema canónico: con
una lista negra, ese campo se publicaría solo, y el corpus contiene procedencia
de prompts, identificadores de ejecución y notas internas de revisión.

También se comprueba aquí lo que decide la publicación: el estado sale de la
revisión jurídica de los elementos proyectados y no de un rótulo. Hoy los 106
casos son `AGENT_REVIEWED`, así que ninguno puede pasar de `internal_preview`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from public_judgment_projection import (
    EstadoPublicacion,
    estado_de_publicacion,
    preceptos_citados,
    proyectar,
    render_public_judgment,
    render_public_judgment_json_schema,
)

PROJECT_ROOT = Path(__file__).parents[1]
CASOS = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "cases"
SENTENCIAS = PROJECT_ROOT / "sentencias"
SCHEMA = PROJECT_ROOT / "schemas" / "residenciafiscal-public-judgment-v1.schema.json"


def cargar(judgment_id: str) -> dict:
    return json.loads((CASOS / f"{judgment_id}.case.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def caso() -> dict:
    return cargar("san-1386-2017")


def test_el_json_schema_versionado_esta_sincronizado() -> None:
    assert SCHEMA.read_text(encoding="utf-8") == render_public_judgment_json_schema()


def test_un_campo_nuevo_del_caso_no_llega_a_la_proyeccion(caso: dict) -> None:
    """Es la razón de ser de la allowlist: publicar es una decisión explícita."""
    contaminado = json.loads(json.dumps(caso))
    contaminado["judgment"]["notas_internas"] = "esto no puede salir"
    contaminado["holdings"][0]["borrador_del_agente"] = "tampoco"

    serializado = render_public_judgment(contaminado)

    assert "notas_internas" not in serializado
    assert "borrador_del_agente" not in serializado
    assert "esto no puede salir" not in serializado


def test_la_procedencia_del_prompt_y_la_ejecucion_no_se_publican(caso: dict) -> None:
    serializado = render_public_judgment(caso)

    assert "prompt_sha256" not in serializado
    assert "promptSha256" not in serializado
    assert "run_id" not in serializado
    assert "runId" not in serializado
    # Pero sí quién generó el análisis: §6.3 exige declarar la procedencia.
    assert "residenciafiscal-hybrid-agent-pipeline" in serializado


def test_las_notas_internas_de_revision_no_se_publican(caso: dict) -> None:
    """Las notas explican decisiones del pipeline, no son contenido editorial."""
    serializado = render_public_judgment(caso)

    assert "Pendiente de aprobación jurídica humana" not in serializado
    # El estado sí sale, porque la ficha tiene que declararlo.
    assert "AGENT_REVIEWED" in serializado


def test_los_anclajes_son_subcadenas_exactas_del_pdf(caso: dict) -> None:
    """Invariante bloqueante: el texto judicial no se reescribe ni se recorta."""
    from verbatim_extraction import extract_verbatim_corpus

    proyeccion = proyectar(caso)
    pdf = PROJECT_ROOT / proyeccion.judgment.source_file
    corpus = extract_verbatim_corpus(
        pdf,
        document_id=proyeccion.judgment.judgment_id,
        source_file=proyeccion.judgment.source_file,
    )
    paginas = {pagina.page_index: pagina.raw_page_text for pagina in corpus.pages}

    for anclaje in proyeccion.anchors:
        for fragmento in anclaje.fragments:
            assert fragmento.verbatim_text in paginas[fragmento.page_index], anclaje.anchor_id


def test_el_hash_del_pdf_se_propaga_sin_cambios(caso: dict) -> None:
    proyeccion = proyectar(caso)

    assert proyeccion.judgment.source_sha256 == caso["judgment"]["source_sha256"]
    for anclaje in proyeccion.anchors:
        assert anclaje.source_sha256 == caso["judgment"]["source_sha256"]


def test_hoy_ningun_caso_supera_internal_preview() -> None:
    """1.620 elementos `AGENT_REVIEWED` y ninguno `HUMAN_APPROVED`."""
    for ruta in sorted(CASOS.glob("*.case.json")):
        proyeccion = proyectar(json.loads(ruta.read_text(encoding="utf-8")))
        assert proyeccion.publication_state == EstadoPublicacion.INTERNAL_PREVIEW


def test_publishable_exige_aprobacion_humana_en_todo_lo_proyectado(caso: dict) -> None:
    aprobado = json.loads(json.dumps(caso))

    def aprobar(elemento: dict) -> None:
        if isinstance(elemento.get("review"), dict):
            elemento["review"]["legal"] = "HUMAN_APPROVED"

    aprobar(aprobado["judgment"])
    for valor in aprobado.values():
        if isinstance(valor, list):
            for item in valor:
                if isinstance(item, dict):
                    aprobar(item)
                    # Los pasos del desempate llevan revisión propia y también
                    # cuentan para el gate.
                    for paso in item.get("steps") or ():
                        aprobar(paso)

    assert estado_de_publicacion(proyectar(aprobado)) == EstadoPublicacion.PUBLISHABLE

    # Basta un anclaje sin aprobar —lo único que reproduce texto judicial— para
    # que la ficha vuelva a preview.
    aprobado["source_anchors"][0]["review"]["legal"] = "AGENT_REVIEWED"
    assert estado_de_publicacion(proyectar(aprobado)) == EstadoPublicacion.INTERNAL_PREVIEW


def test_solo_se_proyectan_los_anclajes_que_la_ficha_usa(caso: dict) -> None:
    """Un anclaje huérfano publicaría texto judicial que nada explica."""
    proyeccion = proyectar(caso)

    usados = {anclaje.anchor_id for anclaje in proyeccion.anchors}
    referenciados = {
        anchor_id
        for cuestion in proyeccion.issues
        for anchor_id in (
            *cuestion.anchor_ids,
            *(cuestion.holding.anchor_ids if cuestion.holding else ()),
        )
    }
    assert referenciados <= usados


def test_el_enlazado_usa_roles_tipados_y_no_countries_en_bruto() -> None:
    """Un país solo mencionado no puede generar un enlace público."""
    caso = cargar("san-1071-2025")
    caso["judgment"] = {**caso["judgment"], "countries": [*caso["judgment"]["countries"], "Kenia"]}

    proyeccion = proyectar(caso)

    codigos = {jurisdiccion.code for jurisdiccion in proyeccion.jurisdictions}
    assert "ke" not in codigos
    assert "fr" in codigos


def test_la_jurisdiccion_enlazada_trae_su_convenio_con_espana() -> None:
    proyeccion = proyectar(cargar("san-1386-2017"))

    suiza = next(j for j in proyeccion.jurisdictions if j.code == "ch")
    assert suiza.treaty_boe_ids == ("BOE-A-1967-3470",)
    assert preceptos_citados(proyeccion) == ("BOE-A-1967-3470",)


def test_el_convenio_enlazado_es_el_que_regia_el_ejercicio_enjuiciado() -> None:
    """El Reino Unido tiene convenio de 1975 y de 2013: el ejercicio decide.

    Enlazar el vigente hoy en un caso de 2011 publicaría, bajo el nombre
    correcto, derecho que entonces no existía.
    """
    proyeccion = proyectar(cargar("san-1226-2021"))

    assert proyeccion.judgment.tax_years == (2011,)
    reino_unido = next(j for j in proyeccion.jurisdictions if j.code == "gb")
    assert reino_unido.treaty_boe_ids == ("BOE-A-1976-23347",)


def test_un_caso_que_cruza_el_cambio_de_convenio_enlaza_los_dos() -> None:
    caso = cargar("san-1226-2021")
    caso["judgment"] = {**caso["judgment"], "tax_years": [2013, 2014]}

    proyeccion = proyectar(caso)

    reino_unido = next(j for j in proyeccion.jurisdictions if j.code == "gb")
    assert reino_unido.treaty_boe_ids == ("BOE-A-1976-23347", "BOE-A-2014-5171")


def test_sin_ejercicios_no_se_declara_ningun_convenio() -> None:
    """Elegir el vigente sería adivinar la época del caso."""
    caso = cargar("san-1226-2021")
    caso["judgment"] = {**caso["judgment"], "tax_years": []}

    proyeccion = proyectar(caso)

    assert all(j.treaty_boe_ids == () for j in proyeccion.jurisdictions)


def test_un_paso_del_convenio_sin_aprobar_bloquea_la_publicacion() -> None:
    """Aprobar el análisis padre no aprueba las conclusiones de sus pasos."""
    caso = cargar("san-1386-2017")
    aprobado = json.loads(json.dumps(caso))

    def aprobar(elemento: dict) -> None:
        if isinstance(elemento.get("review"), dict):
            elemento["review"]["legal"] = "HUMAN_APPROVED"

    aprobar(aprobado["judgment"])
    for valor in aprobado.values():
        if isinstance(valor, list):
            for item in valor:
                if isinstance(item, dict):
                    aprobar(item)
                    for paso in item.get("steps") or ():
                        aprobar(paso)
    assert estado_de_publicacion(proyectar(aprobado)) == EstadoPublicacion.PUBLISHABLE

    aprobado["treaty_analyses"][0]["steps"][0]["review"]["legal"] = "AGENT_REVIEWED"
    assert estado_de_publicacion(proyectar(aprobado)) == EstadoPublicacion.INTERNAL_PREVIEW


def test_se_publica_el_anclaje_que_solo_cita_un_paso_del_convenio() -> None:
    """Sin él, la ficha publicaría una conclusión sin su extracto literal."""
    proyeccion = proyectar(cargar("san-1386-2017"))

    citados = {
        anchor_id
        for cuestion in proyeccion.issues
        for analisis in cuestion.treaty_analyses
        for paso in analisis.steps
        for anchor_id in paso.anchor_ids
    }
    publicados = {anclaje.anchor_id for anclaje in proyeccion.anchors}

    assert citados
    assert citados <= publicados


def test_la_proyeccion_declara_su_jurisdiccion_de_origen(caso: dict) -> None:
    """§7.1: ningún código nuevo asume que la ruta física implica jurisdicción."""
    assert proyectar(caso).jurisdiction == "es"


def test_regenerar_la_proyeccion_dos_veces_da_lo_mismo(caso: dict) -> None:
    assert render_public_judgment(caso) == render_public_judgment(caso)


def test_un_caso_sin_hechos_se_proyecta_igual() -> None:
    """62 de los 67 candidatos no tienen `facts`; la ficha no puede romperse."""
    proyeccion = proyectar(cargar("san-2229-2022"))

    assert proyeccion.issues
    assert all(cuestion.facts == () for cuestion in proyeccion.issues)
    assert proyeccion.anchors
