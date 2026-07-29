"""Contratos del perfil jurídico normalizado que alimenta el bundle OKF."""

from __future__ import annotations

from copy import deepcopy
from typing import cast

import pytest
import yaml
from pydantic import ValidationError

from citation_models import ExtractedPage
from citation_verification import verify_citation_pages
from okf_annotations import JudgmentAnnotations
from okf_models import OkfProvenance
from okf_normalization import normalize_judgment
from okf_rendering import render_judgment_markdown


def _raw_judgment() -> dict[str, object]:
    evidence = {
        "categoria": "SUMINISTROS_Y_CONSUMOS_DOMESTICOS",
        "subcategoria": "suministros vivienda",
        "detalle": "Consumos continuados de agua y electricidad.",
        "objetivo_probatorio": "Acreditar el uso efectivo de la vivienda.",
        "criterio_atacado": "CRIT_VIVIENDA_Y_USO_EFECTIVO",
        "tipo_prueba": "DIRECTA",
        "origen": "OBTENIDA_TERCEROS",
        "aceptada": "SI",
        "peso": 4,
        "motivo_valoracion": "Evidencia una ocupación continuada.",
        "contradiccion_con": "NO CONSTA",
        "cita": {
            "pagina": "3",
            "texto": "suministros de agua y electricidad",
        },
    }
    return {
        "archivo": "SAN_1071_2025.pdf",
        "identificadores": {
            "ROJ": "SAN 1071/2025",
            "ECLI": "ECLI:ES:AN:2025:1071",
        },
        "organo": "Audiencia Nacional, Sección Cuarta",
        "fecha_resolucion": "2025-02-18",
        "es_caso_residencia_irpf": "SI",
        "ejercicios_afectados": "2010 y 2011",
        "pais_alegado_residencia_pf": "Francia",
        "pais_CDI_aplicado": "Francia",
        "se_invoca_CDI": "SI",
        "tiebreaker_paso_decisivo": "NO_APLICA",
        "Criterios_residencia_detectados": [
            "CRIT_183_DIAS",
            "CRIT_CENTRO_INTERESES_ECONOMICOS",
        ],
        "Criterio_decisivo": ["CRIT_CENTRO_INTERESES_ECONOMICOS"],
        "resumen_criterios": "El centro de intereses económicos radica en España.",
        "doctrina_citada": ["Convenio España-Francia"],
        "carga_prueba": {
            "quien_tenia_carga": "AEAT",
            "motivo": "Debía acreditar los hechos constitutivos.",
            "cumplida": "SI",
            "cita": {
                "pagina": "5",
                "texto": "la Administración ha acreditado la residencia",
            },
        },
        "razonamiento_residencia": "La gestión económica se desarrollaba desde España.",
        "Pruebas_AEAT": [evidence],
        "Pruebas_contribuyente": [],
        "Pruebas_rechazadas_clave": [
            {
                "subcategoria": "vivienda en Francia",
                "cita": {"pagina": "4", "texto": "vivienda donde se alega residir"},
            }
        ],
        "Prueba_o_bala_de_plata": {
            "subcategoria": "suministros vivienda",
            "cita": {"pagina": "3", "texto": "suministros de agua y electricidad"},
        },
        "resultado_final": "PARCIAL",
        "frases_clave": [
            {
                "tema": "criterio",
                "pagina": "3",
                "texto": "núcleo principal de sus actividades o intereses económicos",
            },
            {
                "tema": "prueba",
                "pagina": "3",
                "texto": (
                    "movimientos de la tarjeta de crédito... "
                    "restaurantes y repostaje de gasolina... Bescanó"
                ),
            },
        ],
        "confianza_extraccion": "ALTA",
    }


def test_normaliza_el_registro_sin_inventar_el_criterio_invalido() -> None:
    judgment = normalize_judgment(_raw_judgment())

    assert judgment.slug == "san-1071-2025"
    assert judgment.title == "SAN 1071/2025"
    assert judgment.ejercicios_afectados == (2010, 2011)
    assert judgment.paises == ("España", "Francia")
    assert judgment.pruebas_aeat[0].criterio_atacado == "CRIT_OTRO"
    assert judgment.pruebas_aeat[0].source_criterion_atacado == "CRIT_VIVIENDA_Y_USO_EFECTIVO"
    assert judgment.pruebas_aeat[0].normalization_rule == "invalid_criterion_fallback"
    assert judgment.warnings == (
        "Pruebas_AEAT[0].criterio_atacado: CRIT_VIVIENDA_Y_USO_EFECTIVO normalizado a CRIT_OTRO",
    )


def test_los_ids_no_dependen_de_la_posicion_en_la_lista() -> None:
    raw = _raw_judgment()
    original = normalize_judgment(raw)
    reordered = deepcopy(raw)
    evidence = cast(list[dict[str, object]], reordered["Pruebas_AEAT"])
    inserted = deepcopy(evidence[0])
    inserted["subcategoria"] = "otra prueba"
    inserted["detalle"] = "Otra prueba distinta."
    evidence.insert(0, inserted)

    with_insert = normalize_judgment(reordered)

    assert original.pruebas_aeat[0].id == with_insert.pruebas_aeat[1].id
    assert original.pruebas_aeat[0].id.startswith("prueba-aeat-suministros-vivienda-")


def test_extrae_todas_las_citas_anidadas_con_propietario_estable() -> None:
    judgment = normalize_judgment(_raw_judgment())

    assert len(judgment.citas) == 6
    assert len({citation.id for citation in judgment.citas}) == 6
    assert {citation.kind for citation in judgment.citas} == {
        "carga_prueba",
        "prueba_aeat",
        "prueba_rechazada",
        "prueba_decisiva",
        "frase_clave",
    }
    evidence_citation = next(
        citation for citation in judgment.citas if citation.kind == "prueba_aeat"
    )
    assert evidence_citation.owner_id == judgment.pruebas_aeat[0].id
    assert evidence_citation.analysis_quote == "suministros de agua y electricidad"


def test_rechaza_un_enum_invalido_en_los_criterios_de_la_sentencia() -> None:
    raw = _raw_judgment()
    raw["Criterios_residencia_detectados"] = ["CRIT_INVENTADO"]

    with pytest.raises(ValidationError):
        normalize_judgment(raw)


def test_renderiza_okf_y_separa_citas_literales_de_candidatas() -> None:
    raw = _raw_judgment()
    raw["frases_clave"][0]["texto"] = (  # type: ignore[index]
        "nucleo principal de sus actividades o intereses economicos"
    )
    judgment = normalize_judgment(raw)
    pages = (
        ExtractedPage(1, "1", "Portada"),
        ExtractedPage(2, "2", "Antecedentes"),
        ExtractedPage(
            3,
            "3",
            "Que radique el núcleo principal de sus actividades o intereses económicos.",
        ),
        ExtractedPage(
            4,
            "4",
            "Movimientos de la tarjeta de crédito en Bescanó, restaurantes y "
            "los de repostaje de gasolina.",
        ),
    )
    verifications = tuple(
        verify_citation_pages(
            quote=citation.texto,
            declared_page=citation.pagina,
            pages=pages,
            threshold=85,
        )
        for citation in judgment.citas
    )
    provenance = OkfProvenance(
        pdf_resource="../../../sentencias/SAN_1071_2025.pdf",
        pdf_sha256="a" * 64,
        pdf_size_bytes=143201,
        pdf_page_count=4,
        analysis_source="output/analisis_02012026_155032.jsonl",
        analysis_sha256="b" * 64,
        generated_by="residenciafiscal-pipeline/0.1.0",
    )
    annotations = JudgmentAnnotations.model_validate(
        {
            "schema_version": 1,
            "source_file": judgment.archivo,
            "corrections": [
                {
                    "target_id": judgment.pruebas_aeat[0].id,
                    "field": "criterio_atacado",
                    "source_value": "CRIT_OTRO",
                    "replacement": "CRIT_183_DIAS",
                    "rationale": "Pendiente de revisión jurídica.",
                    "status": "proposed",
                }
            ],
            "issues": [
                {
                    "id": "residencia-fiscal",
                    "question": "¿Era residente fiscal en España?",
                    "decision": "GANA_AEAT",
                    "status": "proposed",
                    "support_citation_ids": [judgment.citas[0].id],
                    "source_anchors": [
                        {
                            "pdf_page_index": 3,
                            "source_excerpt_verbatim": (
                                "núcleo principal de sus actividades o intereses económicos"
                            ),
                        }
                    ],
                    "rationale": "Conclusión pendiente de revisión humana.",
                }
            ],
        }
    )

    markdown = render_judgment_markdown(
        judgment,
        provenance,
        verifications,
        annotations=annotations,
    )
    _, raw_frontmatter, body = markdown.split("---", 2)
    frontmatter = yaml.safe_load(raw_frontmatter)

    assert frontmatter["type"] == "Sentencia fiscal"
    assert frontmatter["resource"] == "../../../sentencias/SAN_1071_2025.pdf"
    assert frontmatter["source_sha256"] == "a" * 64
    assert frontmatter["schema_version"] == "residenciafiscal-okf/2"
    assert frontmatter["status"] == "draft"
    assert frontmatter["sources"][0]["id"] == "sentencia-original"
    assert frontmatter["sources"][1] == {
        "id": "analisis-estructurado",
        "resource": "output/analisis_02012026_155032.jsonl",
        "title": "Análisis jurídico estructurado",
        "author": "residenciafiscal-pipeline/0.1.0",
    }
    assert frontmatter["citation_verification"] == {
        "threshold": 85.0,
        "total": 6,
        "evidence_found": 1,
        "literal": 1,
        "pending_review": 5,
    }
    assert frontmatter["human_reviewed"] is False
    assert frontmatter["legal_issues"] == {
        "total": 1,
        "approved": 0,
        "proposed": 1,
    }
    assert "verified" not in frontmatter
    assert "**Regla de lectura:**" in body
    assert "# Cuestión jurídica" in body
    administration_position = body.split("# Posición de la Administración", 1)[1].split(
        "# Posición del contribuyente",
        1,
    )[0]
    assert "- Acreditar el uso efectivo de la vivienda." in administration_position
    assert "# Pruebas valoradas" in body
    assert "# Razonamiento y ratio decidendi" in body
    assert "# Citas literales verificadas" in body
    assert "> núcleo principal de sus actividades o intereses económicos" in body
    assert "> nucleo principal de sus actividades o intereses economicos" not in body
    assert "# Citas pendientes de revisión" in body
    assert "Texto del análisis; no es una cita literal" in body
    assert "restaurantes y repostaje de gasolina" in body
    assert "# Trazabilidad de citas" in body
    assert "# Resultado por cuestiones jurídicas" in body
    assert "¿Era residente fiscal en España?" in body
    assert "> núcleo principal de sus actividades o intereses económicos" in body
    assert "`proposed`" in body
    assert "# Anotaciones y correcciones" in body
    assert "Pendiente de revisión jurídica." in body
    assert judgment.pruebas_aeat[0].id in body
    assert "CRIT_VIVIENDA_Y_USO_EFECTIVO" in body
    assert "[^sentencia-original]" in body
