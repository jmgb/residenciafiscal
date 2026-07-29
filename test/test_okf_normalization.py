"""Contratos del perfil jurídico normalizado que alimenta el bundle OKF."""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from citation_models import ExtractedPage
from citation_verification import verify_citation_pages
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
        },
        "razonamiento_residencia": "La gestión económica se desarrollaba desde España.",
        "Pruebas_AEAT": [evidence],
        "Pruebas_contribuyente": [],
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
    assert judgment.warnings == (
        "Pruebas_AEAT[0].criterio_atacado: CRIT_VIVIENDA_Y_USO_EFECTIVO normalizado a CRIT_OTRO",
    )


def test_rechaza_un_enum_invalido_en_los_criterios_de_la_sentencia() -> None:
    raw = _raw_judgment()
    raw["Criterios_residencia_detectados"] = ["CRIT_INVENTADO"]

    with pytest.raises(ValidationError):
        normalize_judgment(raw)


def test_renderiza_okf_y_separa_citas_literales_de_candidatas() -> None:
    judgment = normalize_judgment(_raw_judgment())
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

    markdown = render_judgment_markdown(judgment, provenance, verifications)
    _, raw_frontmatter, body = markdown.split("---", 2)
    frontmatter = yaml.safe_load(raw_frontmatter)

    assert frontmatter["type"] == "Sentencia fiscal"
    assert frontmatter["resource"] == "../../../sentencias/SAN_1071_2025.pdf"
    assert frontmatter["source_sha256"] == "a" * 64
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
        "total": 2,
        "evidence_found": 1,
        "literal": 1,
        "pending_review": 1,
    }
    assert "verified" not in frontmatter
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
    assert "# Citas pendientes de revisión" in body
    assert "restaurantes y repostaje de gasolina" in body
    assert "[^sentencia-original]" in body
