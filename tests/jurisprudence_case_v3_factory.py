"""Factorías compartidas para los tests del contrato jurisprudencial v3."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def review() -> dict[str, object]:
    return {
        "technical": "VALIDATED",
        "legal": "AGENT_REVIEWED",
        "reviewed_by": "agent:codex",
        "reviewed_at": "2026-07-29",
        "notes": "Pendiente de aprobación jurídica humana.",
    }


def valid_case() -> dict[str, Any]:
    source_sha256 = "a" * 64
    anchor_id = "anchor-residencia-conclusion"
    issue_id = "residencia-fiscal"
    fact_id = "fact-presencia-espana"
    evidence_id = "evidence-vigilancia-vivienda"
    legal_rule_id = "rule-articulo-9-lirpf"
    holding_id = "holding-residencia-fiscal"

    return {
        "schema_version": "residenciafiscal-case/3",
        "judgment": {
            "judgment_id": "san-1210-2023",
            "source_file": "SAN_1210_2023.pdf",
            "roj": "SAN 1210/2023",
            "ecli": "ECLI:ES:AN:2023:1210",
            "court": "Audiencia Nacional",
            "chamber": "Sala de lo Contencioso-Administrativo, Sección Cuarta",
            "decision_date": "2023-02-22",
            "tax_years": [2011, 2013],
            "countries": ["España", "Mónaco"],
            "is_tax_residence_case": True,
            "source_sha256": source_sha256,
            "page_count": 10,
            "extractor": {"name": "pypdf", "version": "6.14.2"},
            "analysis_provenance": {
                "producer": "residenciafiscal-agent-pipeline",
                "model_id": "gpt-5",
                "prompt_sha256": "b" * 64,
                "run_id": "case-v3-pilot-san-1210-2023",
                "generated_at": "2026-07-29T12:00:00Z",
                "input_artifacts": [
                    {
                        "kind": "VERBATIM",
                        "source_path": "knowledge/verbatim/san-1210-2023.pages.json",
                        "sha256": "c" * 64,
                    }
                ],
                "notes": None,
            },
            "review": review(),
        },
        "source_anchors": [
            {
                "anchor_id": anchor_id,
                "source_sha256": source_sha256,
                "fragments": [
                    {
                        "page_index": 8,
                        "printed_page": "8",
                        "start_offset": 100,
                        "end_offset": 128,
                        "verbatim_text": "tiene su residencia efectiva",
                    }
                ],
                "fidelity": "EXACT",
                "purpose": "HOLDING",
                "review": review(),
            }
        ],
        "facts": [
            {
                "fact_id": fact_id,
                "subject_role": "TAXPAYER",
                "category": "PRESENCE",
                "description": "La Sala considera acreditada presencia efectiva en España.",
                "country": "España",
                "place": None,
                "start_date": None,
                "end_date": None,
                "tax_years": [2011, 2013],
                "asserted_by": "COURT",
                "procedural_status": "PROVEN",
                "issue_ids": [issue_id],
                "anchor_ids": [anchor_id],
                "review": review(),
            }
        ],
        "evidence_findings": [
            {
                "evidence_id": evidence_id,
                "offered_by": "AEAT",
                "category": "TESTIFICAL_Y_PERICIAL",
                "subtype": "vigilancia aduanera",
                "description": "Actuaciones de vigilancia en la vivienda española.",
                "probative_purpose": "Acreditar el uso habitual de la vivienda.",
                "fact_ids": [fact_id],
                "issue_ids": [issue_id],
                "assessment": "ACCEPTED",
                "assessment_reason": "Se valora junto con otros indicios concordantes.",
                "role": "CORROBORATIVE",
                "anchor_ids": [anchor_id],
                "review": review(),
            }
        ],
        "legal_rules": [
            {
                "legal_rule_id": legal_rule_id,
                "rule_type": "STATUTE",
                "citation": "Artículo 9 LIRPF",
                "proposition": "La permanencia superior a 183 días determina residencia.",
                "issue_ids": [issue_id],
                "anchor_ids": [anchor_id],
                "review": review(),
            }
        ],
        "holdings": [
            {
                "holding_id": holding_id,
                "issue_id": issue_id,
                "outcome": "GANA_AEAT",
                "conclusion": "El recurrente tenía residencia fiscal en España.",
                "decisive_reasoning": "La prueba indiciaria acredita residencia efectiva.",
                "consequences": ["Sujeción al IRPF por obligación personal."],
                "residence_determination": {
                    "spanish_residence": "RESIDENT_IN_SPAIN",
                    "tax_years": [2011, 2013],
                    "other_country": None,
                    "non_resident_from": None,
                },
                "anchor_ids": [anchor_id],
                "review": review(),
            }
        ],
        "legal_issues": [
            {
                "issue_id": issue_id,
                "question": "¿Tenía el recurrente residencia fiscal en España?",
                "issue_type": "TAX_RESIDENCE",
                "criterion_ids": ["CRIT_183_DIAS"],
                "fact_ids": [fact_id],
                "evidence_ids": [evidence_id],
                "legal_rule_ids": [legal_rule_id],
                "holding_id": holding_id,
                "anchor_ids": [anchor_id],
                "review": review(),
            }
        ],
        "burden_of_proof_steps": [
            {
                "step_id": "burden-administracion-indicios",
                "sequence": 1,
                "issue_ids": [issue_id],
                "fact_to_prove": "Residencia efectiva en España.",
                "initial_bearer": "AEAT",
                "triggering_evidence_ids": [evidence_id],
                "shifts_to": "TAXPAYER",
                "response_required": "Desvirtuar los indicios y acreditar residencia exterior.",
                "conclusion": "La prueba aportada no desvirtuó los indicios.",
                "anchor_ids": [anchor_id],
                "review": review(),
            }
        ],
        "presence_events": [],
        "presence_periods": [],
        "treaty_analyses": [],
        "review": review(),
    }


def case_with_treaty() -> dict[str, Any]:
    raw = deepcopy(valid_case())
    raw["judgment"]["countries"] = ["España", "Suiza"]
    raw["treaty_analyses"] = [
        {
            "treaty_analysis_id": "treaty-spain-switzerland",
            "countries": ["España", "Suiza"],
            "treaty_citation": "Artículo 4 del CDI entre España y Suiza",
            "domestic_law_issue_ids": ["residencia-fiscal"],
            "dual_residence_established": True,
            "steps": [
                {
                    "step_id": "treaty-step-permanent-home",
                    "sequence": 1,
                    "criterion": "VIVIENDA_PERMANENTE",
                    "applied": True,
                    "conclusion": "Existía vivienda permanente a disposición.",
                    "fact_ids": ["fact-presencia-espana"],
                    "evidence_ids": ["evidence-vigilancia-vivienda"],
                    "anchor_ids": ["anchor-residencia-conclusion"],
                    "review": review(),
                }
            ],
            "decisive_step_id": "treaty-step-permanent-home",
            "result_country": "Suiza",
            "anchor_ids": ["anchor-residencia-conclusion"],
            "review": review(),
        }
    ]
    return raw
