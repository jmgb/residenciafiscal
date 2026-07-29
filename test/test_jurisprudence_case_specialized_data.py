"""Datos especializados necesarios para días y documentación extranjera."""

from copy import deepcopy

import pytest
from jurisprudence_case_v3_factory import valid_case
from pydantic import ValidationError


def test_representa_un_evento_y_un_periodo_de_presencia_tipados() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = valid_case()
    raw["presence_events"] = [
        {
            "event_id": "presence-entry-spain",
            "event_type": "ENTRY",
            "event_date": "2013-01-10",
            "date_precision": "EXACT",
            "country": "España",
            "place": "Madrid",
            "subject_role": "TAXPAYER",
            "asserted_by": "COURT",
            "procedural_status": "PROVEN",
            "fact_ids": ["fact-presencia-espana"],
            "evidence_ids": ["evidence-vigilancia-vivienda"],
            "issue_ids": ["residencia-fiscal"],
            "anchor_ids": ["anchor-residencia-conclusion"],
            "review": raw["review"],
        }
    ]
    raw["presence_periods"] = [
        {
            "period_id": "presence-period-spain-2013",
            "classification": "PRESENT",
            "start_date": "2013-01-10",
            "end_date": "2013-07-20",
            "country": "España",
            "day_count": 192,
            "calculation_method": "Días naturales entre entrada y salida.",
            "counted_for_183_day_rule": True,
            "determined_by": "COURT",
            "fact_ids": ["fact-presencia-espana"],
            "evidence_ids": ["evidence-vigilancia-vivienda"],
            "issue_ids": ["residencia-fiscal"],
            "anchor_ids": ["anchor-residencia-conclusion"],
            "review": raw["review"],
        }
    ]

    case = JurisprudenceCase.model_validate(raw)

    assert case.presence_events[0].event_date.isoformat() == "2013-01-10"
    assert case.presence_periods[0].day_count == 192


def test_periodo_de_presencia_rechaza_fechas_invertidas() -> None:
    from jurisprudence_case_timeline import PresencePeriod

    raw = valid_case()
    period = {
        "period_id": "presence-period-invalid",
        "classification": "PRESENT",
        "start_date": "2013-07-20",
        "end_date": "2013-01-10",
        "country": "España",
        "day_count": 192,
        "calculation_method": "Cómputo declarado.",
        "counted_for_183_day_rule": True,
        "determined_by": "COURT",
        "fact_ids": ["fact-presencia-espana"],
        "evidence_ids": ["evidence-vigilancia-vivienda"],
        "issue_ids": ["residencia-fiscal"],
        "anchor_ids": ["anchor-residencia-conclusion"],
        "review": raw["review"],
    }

    with pytest.raises(ValidationError, match="end_date"):
        PresencePeriod.model_validate(period)


@pytest.mark.parametrize(
    ("collection", "field", "missing_id"),
    [
        ("presence_events", "fact_ids", "fact-inexistente"),
        ("presence_events", "evidence_ids", "evidence-inexistente"),
        ("presence_periods", "issue_ids", "issue-inexistente"),
        ("presence_periods", "anchor_ids", "anchor-inexistente"),
    ],
)
def test_cronologia_solo_referencia_elementos_del_mismo_caso(
    collection: str,
    field: str,
    missing_id: str,
) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = valid_case()
    raw["presence_events"] = [
        {
            "event_id": "presence-entry-spain",
            "event_type": "ENTRY",
            "event_date": "2013-01-10",
            "date_precision": "EXACT",
            "country": "España",
            "place": None,
            "subject_role": "TAXPAYER",
            "asserted_by": "COURT",
            "procedural_status": "PROVEN",
            "fact_ids": ["fact-presencia-espana"],
            "evidence_ids": ["evidence-vigilancia-vivienda"],
            "issue_ids": ["residencia-fiscal"],
            "anchor_ids": ["anchor-residencia-conclusion"],
            "review": raw["review"],
        }
    ]
    raw["presence_periods"] = [
        {
            "period_id": "presence-period-spain",
            "classification": "PRESENT",
            "start_date": "2013-01-10",
            "end_date": "2013-01-11",
            "country": "España",
            "day_count": 2,
            "calculation_method": "Dos días naturales.",
            "counted_for_183_day_rule": True,
            "determined_by": "COURT",
            "fact_ids": ["fact-presencia-espana"],
            "evidence_ids": ["evidence-vigilancia-vivienda"],
            "issue_ids": ["residencia-fiscal"],
            "anchor_ids": ["anchor-residencia-conclusion"],
            "review": raw["review"],
        }
    ]
    raw[collection][0][field] = [missing_id]

    with pytest.raises(ValidationError, match=missing_id):
        JurisprudenceCase.model_validate(raw)


def test_documento_fiscal_extranjero_conserva_atributos_probatorios() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = valid_case()
    evidence = raw["evidence_findings"][0]
    evidence.update(
        {
            "category": "DOCUMENTACION_FISCAL_EXTRANJERA",
            "subtype": "certificado de residencia fiscal",
            "foreign_document": {
                "document_type": "TAX_RESIDENCE_CERTIFICATE",
                "issuing_authority": "Administration fédérale des contributions",
                "jurisdiction": "Suiza",
                "period_start": "2013-01-01",
                "period_end": "2013-12-31",
                "nature": "TAX",
                "tax_scope": "WORLDWIDE_INCOME",
                "defects": [],
                "probative_effect": "Acredita sujeción fiscal durante el ejercicio.",
            },
        }
    )

    case = JurisprudenceCase.model_validate(raw)

    document = case.evidence_findings[0].foreign_document
    assert document is not None
    assert document.tax_scope == "WORLDWIDE_INCOME"


def test_categoria_documental_extranjera_exige_detalle_tipado() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    raw["evidence_findings"][0]["category"] = "DOCUMENTACION_FISCAL_EXTRANJERA"

    with pytest.raises(ValidationError, match="foreign_document"):
        JurisprudenceCase.model_validate(raw)
