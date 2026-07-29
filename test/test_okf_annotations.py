"""Contratos de las anotaciones humanas separadas de los datos generados."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from test_okf_normalization import _raw_judgment

from citation_models import ExtractedPage
from okf_annotations import (
    JudgmentAnnotations,
    apply_approved_corrections,
    load_annotations,
    validate_annotation_references,
    validate_source_anchors,
)
from okf_normalization import normalize_judgment


def _annotations(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "schema_version": 1,
        "source_file": "SAN_1071_2025.pdf",
        "corrections": [],
        "issues": [],
    }
    values.update(overrides)
    return values


def test_un_sidecar_ausente_equivale_a_anotaciones_vacias(tmp_path: Path) -> None:
    annotations = load_annotations(tmp_path / "inexistente.yaml", "SAN_1071_2025.pdf")

    assert annotations == JudgmentAnnotations(
        schema_version=1,
        source_file="SAN_1071_2025.pdf",
    )


def test_prohibe_corregir_o_sustituir_texto_legal() -> None:
    correction = {
        "target_id": "cita-1",
        "field": "source_excerpt_verbatim",
        "source_value": "texto original",
        "replacement": "texto reescrito",
        "rationale": "No debe permitirse.",
        "status": "proposed",
    }

    with pytest.raises(ValidationError, match="texto legal"):
        JudgmentAnnotations.model_validate(_annotations(corrections=[correction]))


def test_una_correccion_aprobada_exige_identidad_y_fecha_de_revision() -> None:
    correction = {
        "target_id": "prueba-1",
        "field": "criterio_atacado",
        "source_value": "CRIT_OTRO",
        "replacement": "CRIT_183_DIAS",
        "rationale": "Clasificación revisada.",
        "status": "approved",
    }

    with pytest.raises(ValidationError, match="reviewed_by"):
        JudgmentAnnotations.model_validate(_annotations(corrections=[correction]))


def test_rechaza_un_valor_de_reemplazo_fuera_del_catalogo() -> None:
    correction = {
        "target_id": "prueba-1",
        "field": "criterio_atacado",
        "source_value": "CRIT_OTRO",
        "replacement": "CRIT_INVENTADO",
        "rationale": "No debe permitirse.",
        "status": "proposed",
    }

    with pytest.raises(ValidationError, match="reemplazo no canónico"):
        JudgmentAnnotations.model_validate(_annotations(corrections=[correction]))


def test_solo_aplica_correcciones_aprobadas_a_metadatos_derivados() -> None:
    judgment = normalize_judgment(_raw_judgment())
    evidence_id = judgment.pruebas_aeat[0].id
    corrections = [
        {
            "target_id": evidence_id,
            "field": "criterio_atacado",
            "source_value": "CRIT_OTRO",
            "replacement": "CRIT_183_DIAS",
            "rationale": "Propuesta pendiente.",
            "status": "proposed",
        },
        {
            "target_id": evidence_id,
            "field": "criterio_atacado",
            "source_value": "CRIT_OTRO",
            "replacement": "CRIT_CENTRO_INTERESES_ECONOMICOS",
            "rationale": "Revisión jurídica aprobada.",
            "status": "approved",
            "reviewed_by": "human:revisor-juridico",
            "reviewed_at": "2026-07-29",
        },
    ]
    annotations = JudgmentAnnotations.model_validate(_annotations(corrections=corrections))

    corrected = apply_approved_corrections(judgment, annotations)

    assert corrected.pruebas_aeat[0].criterio_atacado == ("CRIT_CENTRO_INTERESES_ECONOMICOS")
    assert corrected.pruebas_aeat[0].source_criterion_atacado == ("CRIT_VIVIENDA_Y_USO_EFECTIVO")


def test_valida_referencias_y_carga_resultados_por_cuestion(tmp_path: Path) -> None:
    judgment = normalize_judgment(_raw_judgment())
    citation_id = judgment.citas[0].id
    sidecar = _annotations(
        issues=[
            {
                "id": "residencia-fiscal",
                "question": "¿Era residente fiscal en España?",
                "decision": "GANA_AEAT",
                "status": "proposed",
                "support_citation_ids": [citation_id],
                "rationale": "Resultado estructurado pendiente de revisión humana.",
            }
        ]
    )
    sidecar_path = tmp_path / "san-1071-2025.yaml"
    sidecar_path.write_text(
        yaml.safe_dump(sidecar, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    annotations = load_annotations(sidecar_path, judgment.archivo)
    validate_annotation_references(judgment, annotations)

    assert annotations.issues[0].decision == "GANA_AEAT"
    assert annotations.issues[0].support_citation_ids == (citation_id,)


def test_rechaza_una_referencia_a_cita_inexistente() -> None:
    judgment = normalize_judgment(_raw_judgment())
    annotations = JudgmentAnnotations.model_validate(
        _annotations(
            issues=[
                {
                    "id": "sancion",
                    "question": "¿Se anula la sanción?",
                    "decision": "GANA_CONTRIBUYENTE",
                    "status": "proposed",
                    "support_citation_ids": ["cita-inexistente"],
                    "rationale": "Fallo.",
                }
            ]
        )
    )

    with pytest.raises(ValueError, match="cita-inexistente"):
        validate_annotation_references(judgment, annotations)


def test_rechaza_un_anclaje_que_no_sea_subcadena_literal_del_pdf() -> None:
    annotations = JudgmentAnnotations.model_validate(
        _annotations(
            issues=[
                {
                    "id": "sancion",
                    "question": "¿Se anula la sanción?",
                    "decision": "GANA_CONTRIBUYENTE",
                    "status": "proposed",
                    "support_citation_ids": [],
                    "source_anchors": [
                        {
                            "pdf_page_index": 1,
                            "source_excerpt_verbatim": "no concurre culpabilidad infractora",
                        }
                    ],
                    "rationale": "Fallo.",
                }
            ]
        )
    )
    pages = (
        ExtractedPage(
            1,
            "1",
            "Por ello entendemos que no concurre culpabilidad infractora.",
        ),
    )

    validate_source_anchors(annotations, pages)
    altered = annotations.model_copy(
        update={
            "issues": (
                annotations.issues[0].model_copy(
                    update={
                        "source_anchors": (
                            annotations.issues[0]
                            .source_anchors[0]
                            .model_copy(
                                update={
                                    "source_excerpt_verbatim": (
                                        "No concurre culpabilidad infractora"
                                    )
                                }
                            ),
                        )
                    }
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="no es literal"):
        validate_source_anchors(altered, pages)
