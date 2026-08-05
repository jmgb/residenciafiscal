"""Conversión conservadora del análisis legado en borradores v3."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from jurisprudence_case_catalogs import CriterionId, EvidenceCategory
from jurisprudence_legacy_anchors import LocatedFragment, locate_exact_fragments
from verbatim_models import VerbatimCorpus

_SENTINELS = {"", "NO APLICA", "NO CONSTA", "NINGUNO", "N/A"}
_OUTCOMES = {
    "GANA_AEAT",
    "GANA_CONTRIBUYENTE",
    "PARCIAL",
    "RETROACCION",
    "INADMISION",
    "NO_RESUELTO",
}


@dataclass(frozen=True)
class LegacyCaseDraft:
    proposal: dict[str, Any]
    evaluation: dict[str, Any]


def _review() -> dict[str, object]:
    return {
        "technical": "VALIDATED",
        "legal": "AGENT_REVIEWED",
        "reviewed_by": "agent:codex",
        "reviewed_at": "2026-08-01",
        "notes": "Borrador conservador derivado del análisis legado; sin aprobación humana.",
    }


def _text(value: object, fallback: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _tax_years(value: object) -> list[int]:
    return sorted({int(item) for item in re.findall(r"\b(?:19|20)\d{2}\b", str(value))})


def _countries(record: dict[str, object]) -> list[str]:
    countries = ["España"]
    for field in ("pais_alegado_residencia_pf", "pais_CDI_aplicado"):
        value = _text(record.get(field), "")
        if value.upper() not in _SENTINELS and value not in countries:
            countries.append(value)
    return countries


def _judgment_id(source_file: str) -> str:
    return source_file.removesuffix(".pdf").lower().replace("_", "-")


def _fallback_fragment(verbatim: VerbatimCorpus) -> LocatedFragment:
    for page in reversed(verbatim.pages):
        upper = page.raw_page_text.upper()
        start = upper.find("FALLAMOS")
        if start >= 0:
            text = page.raw_page_text[start : start + 600].rstrip()
            return LocatedFragment(page.page_index, start, start + len(text), text)
    page = next(item for item in verbatim.pages if item.raw_page_text)
    text = page.raw_page_text[:600].rstrip()
    return LocatedFragment(page.page_index, 0, len(text), text)


def _anchor(anchor_id: str, fragments: tuple[LocatedFragment, ...], purpose: str) -> dict[str, Any]:
    return {
        "anchor_id": anchor_id,
        "fragments": [
            {"page_index": item.page_index, "verbatim_text": item.verbatim_text}
            for item in fragments
        ],
        "fidelity": "EXACT_WITH_ELLIPSIS" if len(fragments) > 1 else "EXACT",
        "purpose": purpose,
        "review": _review(),
    }


def _assessment(value: object) -> str:
    return {"SI": "ACCEPTED", "NO": "REJECTED", "PARCIAL": "PARTIAL"}.get(
        str(value).upper(), "UNRESOLVED"
    )


def _evidence_category(value: object) -> str:
    candidate = str(value)
    return candidate if candidate in {item.value for item in EvidenceCategory} else "OTROS"


def _evidence(
    record: dict[str, object], verbatim: VerbatimCorpus
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    anchors: list[dict[str, Any]] = []
    groups = (("Pruebas_AEAT", "AEAT"), ("Pruebas_contribuyente", "TAXPAYER"))
    for field, offered_by in groups:
        values = record.get(field)
        if not isinstance(values, list):
            continue
        for raw in values:
            if not isinstance(raw, dict) or not isinstance(raw.get("cita"), dict):
                continue
            citation = raw["cita"]
            quote = citation.get("texto")
            if not isinstance(quote, str):
                continue
            fragments = locate_exact_fragments(
                quote,
                declared_page=citation.get("pagina"),
                verbatim=verbatim,
            )
            if not fragments:
                continue
            index = len(findings) + 1
            evidence_id = f"evidence-legacy-{index:03d}"
            anchor_id = f"anchor-legacy-evidence-{index:03d}"
            category = _evidence_category(raw.get("categoria"))
            assessment = _assessment(raw.get("aceptada"))
            finding: dict[str, Any] = {
                "evidence_id": evidence_id,
                "offered_by": offered_by,
                "category": category,
                "subtype": _text(raw.get("subcategoria"), "Prueba descrita en análisis legado"),
                "description": _text(raw.get("detalle"), "Prueba descrita en análisis legado."),
                "probative_purpose": _text(
                    raw.get("objetivo_probatorio"), "Finalidad no explicitada."
                ),
                "fact_ids": [],
                "issue_ids": ["residencia-fiscal"],
                "assessment": assessment,
                "assessment_reason": (
                    _text(raw.get("motivo_valoracion"), "Valoración recogida en análisis legado.")
                    if assessment not in {"UNRESOLVED", "NOT_ASSESSED"}
                    else None
                ),
                "role": "DECISIVE" if raw.get("peso") == 5 else "CORROBORATIVE",
                "anchor_ids": [anchor_id],
                "review": _review(),
            }
            if category == "DOCUMENTACION_FISCAL_EXTRANJERA":
                finding["foreign_document"] = {
                    "document_type": "OTHER",
                    "issuing_authority": None,
                    "jurisdiction": _countries(record)[-1],
                    "period_start": None,
                    "period_end": None,
                    "nature": "TAX",
                    "tax_scope": "NOT_STATED",
                    "defects": [],
                    "probative_effect": _text(raw.get("motivo_valoracion"), "No consta."),
                }
            findings.append(finding)
            anchors.append(_anchor(anchor_id, fragments, "EVIDENCE"))
    return findings, anchors


def _supplemental_anchors(
    record: dict[str, object], verbatim: VerbatimCorpus
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    candidates: list[tuple[str, object]] = []
    rejected = record.get("Pruebas_rechazadas_clave")
    if isinstance(rejected, list):
        candidates.extend(
            ("REASONING", item.get("cita")) for item in rejected if isinstance(item, dict)
        )
    burden = record.get("carga_prueba")
    if isinstance(burden, dict):
        candidates.append(("BURDEN_OF_PROOF", burden.get("cita")))
    key_phrases = record.get("frases_clave")
    if isinstance(key_phrases, list):
        for item in key_phrases:
            if not isinstance(item, dict):
                continue
            topic = str(item.get("tema", "")).casefold()
            purpose = (
                "BURDEN_OF_PROOF"
                if "carga" in topic
                else "HOLDING"
                if topic in {"criterio", "resultado"}
                else "REASONING"
            )
            candidates.append((purpose, item))

    anchors: list[dict[str, Any]] = []
    anchor_ids: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, tuple[tuple[int, int, int], ...]]] = set()
    counters: dict[str, int] = defaultdict(int)
    prefix = {
        "BURDEN_OF_PROOF": "burden",
        "HOLDING": "holding",
        "REASONING": "reasoning",
    }
    for purpose, raw_citation in candidates:
        if not isinstance(raw_citation, dict):
            continue
        quote = raw_citation.get("texto")
        if not isinstance(quote, str):
            continue
        fragments = locate_exact_fragments(
            quote,
            declared_page=raw_citation.get("pagina"),
            verbatim=verbatim,
        )
        signature = tuple(
            (item.page_index, item.start_offset, item.end_offset) for item in fragments
        )
        if not fragments or (purpose, signature) in seen:
            continue
        seen.add((purpose, signature))
        counters[purpose] += 1
        anchor_id = f"anchor-legacy-{prefix[purpose]}-{counters[purpose]:03d}"
        anchors.append(_anchor(anchor_id, fragments, purpose))
        anchor_ids[purpose].append(anchor_id)
    return anchors, dict(anchor_ids)


def _burden_steps(
    record: dict[str, object],
    *,
    issue_id: str,
    anchor_ids: list[str],
) -> list[dict[str, Any]]:
    burden = record.get("carga_prueba")
    if not anchor_ids or not isinstance(burden, dict):
        return []
    bearer = {
        "AEAT": "AEAT",
        "ADMINISTRACION": "AEAT",
        "ADMINISTRACIÓN": "AEAT",
        "CONTRIBUYENTE": "TAXPAYER",
        "AMBOS": "BOTH",
        "TRIBUNAL": "COURT",
    }.get(str(burden.get("quien_tenia_carga", "")).upper(), "OTHER")
    fulfilled = str(burden.get("cumplida", "")).upper() == "SI"
    shifts_to = "TAXPAYER" if fulfilled and bearer == "AEAT" else None
    return [
        {
            "step_id": "burden-legacy-001",
            "sequence": 1,
            "issue_ids": [issue_id],
            "fact_to_prove": _text(
                burden.get("motivo"), "Hecho sujeto a la distribución de la carga probatoria."
            ),
            "initial_bearer": bearer,
            "triggering_evidence_ids": [],
            "shifts_to": shifts_to,
            "response_required": (
                "Desvirtuar los indicios y acreditar la residencia exterior." if shifts_to else None
            ),
            "conclusion": (
                "La carga probatoria se consideró cumplida."
                if fulfilled
                else "La carga probatoria no se consideró cumplida."
            ),
            "anchor_ids": anchor_ids,
            "review": _review(),
        }
    ]


def build_legacy_case_draft(
    record: dict[str, object],
    *,
    verbatim: VerbatimCorpus,
    verbatim_resource: str,
    legacy_resource: str,
    generated_at: datetime,
) -> LegacyCaseDraft:
    """Construye el mínimo publicable como borrador, sin inventar aprobación."""

    source_file = _text(record.get("archivo"), verbatim.source_file.rsplit("/", 1)[-1])
    identifiers = record.get("identificadores")
    identifiers = identifiers if isinstance(identifiers, dict) else {}
    in_scope = str(record.get("es_caso_residencia_irpf")).upper() == "SI"
    issue_id = "residencia-fiscal" if in_scope else "fuera-de-alcance"
    evidence, anchors = _evidence(record, verbatim) if in_scope else ([], [])
    supplemental, supplemental_ids = (
        _supplemental_anchors(record, verbatim) if in_scope else ([], {})
    )
    anchors.extend(supplemental)
    if not anchors:
        fallback = _fallback_fragment(verbatim)
        anchors = [_anchor("anchor-legacy-decision", (fallback,), "HOLDING")]
    holding_anchor_ids = supplemental_ids.get("HOLDING", [])
    if not holding_anchor_ids:
        holding_anchor_ids = [anchors[0]["anchor_id"]]
    holding_anchor = holding_anchor_ids[0]
    years = _tax_years(record.get("ejercicios_afectados"))
    raw_criteria = record.get("Criterios_residencia_detectados")
    criteria_values = raw_criteria if isinstance(raw_criteria, list) else []
    criteria = (
        [
            item
            for item in criteria_values
            if isinstance(item, str)
            if item in {criterion.value for criterion in CriterionId}
        ]
        if in_scope
        else []
    )
    reasoning = _text(
        record.get("razonamiento_residencia") or record.get("resumen_criterios"),
        "El análisis legado no contiene razonamiento residencial adicional.",
    )
    conclusion = (
        reasoning
        if in_scope
        else _text(
            record.get("motivo_fuera_de_alcance"), "Resolución fuera del alcance residencial."
        )
    )
    outcome = str(record.get("resultado_final"))
    outcome = outcome if outcome in _OUTCOMES else "OTROS"
    roj = _text(identifiers.get("ROJ"), source_file.removesuffix(".pdf"))
    evaluation_context = _text(record.get("resumen_criterios"), reasoning)
    evaluation_question = (
        f"¿Cómo resolvió {roj} este supuesto de residencia: {evaluation_context[:240]}?"
        if in_scope
        else f"¿Por qué {roj} está fuera del alcance residencial?"
    )
    proposal = {
        "schema_version": "residenciafiscal-case/3",
        "judgment": {
            "judgment_id": _judgment_id(source_file),
            "source_file": f"sentencias/{source_file}",
            "roj": roj,
            "ecli": _text(identifiers.get("ECLI"), f"NO-CONSTA:{_judgment_id(source_file)}"),
            "court": _text(record.get("organo"), "Órgano no consignado en análisis legado"),
            "chamber": None,
            "decision_date": _text(record.get("fecha_resolucion"), generated_at.date().isoformat()),
            "tax_years": years,
            "countries": _countries(record),
            "is_tax_residence_case": in_scope,
            "analysis_provenance": {
                "producer": "residenciafiscal-legacy-bootstrap",
                "model_id": "legacy-analysis-agent-reviewed",
                "prompt_sha256": None,
                "run_id": f"legacy-bootstrap-{_judgment_id(source_file)}",
                "generated_at": generated_at.isoformat(),
                "input_artifacts": [
                    {"kind": "VERBATIM", "source_path": verbatim_resource},
                    {"kind": "LEGACY_ANALYSIS", "source_path": legacy_resource},
                ],
                "notes": "Migración conservadora; la determinación residencial no se infiere del resultado global.",
            },
            "review": _review(),
        },
        "source_anchors": anchors,
        "facts": [],
        "evidence_findings": evidence,
        "legal_rules": [],
        "holdings": [
            {
                "holding_id": f"holding-{issue_id}",
                "issue_id": issue_id,
                "outcome": outcome,
                "conclusion": conclusion,
                "decisive_reasoning": reasoning,
                "consequences": [],
                "residence_determination": (
                    {
                        "spanish_residence": "NOT_DECIDED",
                        "tax_years": years,
                        "other_country": None,
                        "non_resident_from": None,
                    }
                    if in_scope and years
                    else None
                ),
                "anchor_ids": holding_anchor_ids,
                "review": _review(),
            }
        ],
        "legal_issues": [
            {
                "issue_id": issue_id,
                "question": "¿Qué decidió la resolución sobre la residencia fiscal?"
                if in_scope
                else "¿Está la resolución dentro del corpus residencial?",
                "issue_type": "TAX_RESIDENCE" if in_scope else "OTHER",
                "criterion_ids": criteria,
                "fact_ids": [],
                "evidence_ids": [item["evidence_id"] for item in evidence],
                "legal_rule_ids": [],
                "holding_id": f"holding-{issue_id}",
                "anchor_ids": [item["anchor_id"] for item in anchors],
                "review": _review(),
            }
        ],
        "burden_of_proof_steps": _burden_steps(
            record,
            issue_id=issue_id,
            anchor_ids=supplemental_ids.get("BURDEN_OF_PROOF", []),
        ),
        "presence_events": [],
        "presence_periods": [],
        "treaty_analyses": [],
        "review": _review(),
    }
    evaluation = {
        "schema_version": "residenciafiscal-case-question-evaluation/1",
        "judgment_id": _judgment_id(source_file),
        "questions": [
            {
                "question_id": "LEGACY-01",
                "question": evaluation_question,
                "required_issue_ids": [issue_id],
                "required_fact_ids": [],
                "required_evidence_ids": [item["evidence_id"] for item in evidence],
                "required_anchor_ids": [holding_anchor],
                "expected_behavior": "Usar solo el contenido estructurado y sus anclajes literales.",
                "limitations": "Borrador AGENT_REVIEWED sin aprobación jurídica humana.",
            }
        ],
    }
    return LegacyCaseDraft(proposal=proposal, evaluation=evaluation)
