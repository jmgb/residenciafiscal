"""Renderizado determinista del perfil jurídico como concepto OKF v0.2."""

from __future__ import annotations

from collections.abc import Sequence

import yaml

from citation_models import CitationVerification
from citation_verification import DEFAULT_THRESHOLD
from okf_annotation_rendering import annotation_quality, render_annotation_sections
from okf_annotations import JudgmentAnnotations
from okf_models import OkfJudgment, OkfProvenance
from okf_render_sections import (
    render_citation_sections,
    render_evidence_table,
    render_position,
)


def _description(judgment: OkfJudgment) -> str:
    decisive = ", ".join(judgment.criterios_decisivos) or "criterio no determinado"
    return f"Residencia fiscal analizada mediante {decisive}; resultado {judgment.resultado_final}."


def _frontmatter(
    judgment: OkfJudgment,
    provenance: OkfProvenance,
    verifications: Sequence[CitationVerification],
    threshold: float,
    annotations: JudgmentAnnotations,
) -> dict[str, object]:
    literal = sum(verification.publishable_literal for verification in verifications)
    evidence_found = sum(verification.evidence_found for verification in verifications)
    pending = len(verifications) - literal
    status = "draft" if judgment.warnings or pending else "stable"
    return {
        "type": "Sentencia fiscal",
        "title": judgment.title,
        "description": _description(judgment),
        "resource": provenance.pdf_resource,
        "tags": [
            "residencia-fiscal",
            judgment.resultado_final.lower(),
            *(criterion.lower() for criterion in judgment.criterios_decisivos),
        ],
        "status": status,
        "roj": judgment.roj,
        "ecli": judgment.ecli,
        "organo": judgment.organo,
        "fecha_resolucion": judgment.fecha_resolucion,
        "ejercicios_afectados": list(judgment.ejercicios_afectados),
        "paises": list(judgment.paises),
        "cdi_aplicado": judgment.pais_cdi_aplicado,
        "criterios_detectados": list(judgment.criterios_detectados),
        "criterios_decisivos": list(judgment.criterios_decisivos),
        "resultado": judgment.resultado_final,
        "confianza_extraccion": judgment.confianza_extraccion,
        "source_sha256": provenance.pdf_sha256,
        "analysis_sha256": provenance.analysis_sha256,
        "schema_version": "residenciafiscal-okf/2",
        "sources": [
            {
                "id": "sentencia-original",
                "resource": provenance.pdf_resource,
                "title": f"{judgment.title} — PDF original del CENDOJ",
                "author": "CENDOJ/official",
            },
            {
                "id": "analisis-estructurado",
                "resource": provenance.analysis_source,
                "title": "Análisis jurídico estructurado",
                "author": provenance.generated_by,
            },
        ],
        "generated": {"by": provenance.generated_by},
        "citation_verification": {
            "threshold": threshold,
            "total": len(verifications),
            "evidence_found": evidence_found,
            "literal": literal,
            "pending_review": pending,
        },
        **annotation_quality(annotations),
    }


def render_judgment_markdown(
    judgment: OkfJudgment,
    provenance: OkfProvenance,
    verifications: Sequence[CitationVerification],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    annotations: JudgmentAnnotations | None = None,
    verification_report_resource: str | None = None,
) -> str:
    """Renderiza un concepto estable; exige un resultado por cita y en el mismo orden."""

    if len(judgment.citas) != len(verifications):
        raise ValueError("Cada cita debe tener exactamente un resultado de verificación")
    annotations = annotations or JudgmentAnnotations(
        schema_version=1,
        source_file=judgment.archivo,
    )
    frontmatter = yaml.safe_dump(
        _frontmatter(judgment, provenance, verifications, threshold, annotations),
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    years = ", ".join(map(str, judgment.ejercicios_afectados)) or "no determinados"
    lines = [
        "---",
        frontmatter,
        "---",
        "",
        "**Regla de lectura:** el contenido narrativo procede del análisis "
        "estructurado. Solo los bloques identificados como «extracto literal del PDF» "
        "o incluidos en «Citas literales verificadas» reproducen texto de la sentencia.",
        "",
        "# Cuestión jurídica",
        "",
        f"Determinar la residencia fiscal de una persona física en los ejercicios "
        f"{years}, con residencia alegada en {judgment.pais_alegado_residencia_pf}.",
        "",
        "# Hechos relevantes",
        "",
        judgment.resumen_criterios,
        "",
        "# Posición de la Administración",
        "",
        *render_position(judgment.pruebas_aeat),
        "",
        "# Posición del contribuyente",
        "",
        *render_position(judgment.pruebas_contribuyente),
        "",
        "# Pruebas valoradas",
        "",
        *render_evidence_table("Pruebas de la AEAT", judgment.pruebas_aeat),
        "",
        *render_evidence_table(
            "Pruebas del contribuyente",
            judgment.pruebas_contribuyente,
        ),
        "",
        "# Carga de la prueba",
        "",
        f"- Parte: `{judgment.carga_prueba.quien_tenia_carga}`",
        f"- Cumplida: `{judgment.carga_prueba.cumplida}`",
        f"- Motivo: {judgment.carga_prueba.motivo}",
        "",
        "# Normas y jurisprudencia citadas",
        "",
        *(f"- {item}" for item in judgment.doctrina_citada),
        "",
        "# Razonamiento y ratio decidendi",
        "",
        judgment.razonamiento_residencia,
        "",
        "# Fallo",
        "",
        f"Resultado estructurado: `{judgment.resultado_final}`.",
        "",
        *render_annotation_sections(annotations),
        "",
        *render_citation_sections(judgment, verifications),
        "",
        "# Calidad y procedencia",
        "",
        f"- Confianza de la extracción: `{judgment.confianza_extraccion}`.",
        f"- PDF: `{provenance.pdf_sha256}` ({provenance.pdf_page_count} páginas, "
        f"{provenance.pdf_size_bytes} bytes).",
        f"- JSONL: `{provenance.analysis_sha256}` (`{provenance.analysis_source}`).",
        *(
            [
                "- Trazabilidad de citas (IDs completos, campo de origen y "
                f"puntuaciones): [informe de verificación]({verification_report_resource})."
            ]
            if verification_report_resource
            else []
        ),
        *(f"- Advertencia: {warning}." for warning in judgment.warnings),
        "",
        "[^sentencia-original]: Resolución original del CENDOJ indicada en `sources`.",
        "",
    ]
    return "\n".join(lines)
