"""Normalización determinista del JSONL al perfil jurídico OKF."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from config import VALID_CRITERIOS
from okf_citation_normalization import extract_nested_citations
from okf_models import OkfBurdenOfProof, OkfEvidence, OkfJudgment
from okf_stable_ids import slugify, stable_id

_MISSING_VALUES = {"", "NO CONSTA", "NO APLICA", "NO_APLICA"}


def _as_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} debe ser un objeto")
    return cast(Mapping[str, object], value)


def _as_sequence(value: object, field: str) -> Sequence[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} debe ser una lista")
    return value


def _text(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} debe ser texto no vacío")
    return value.strip()


def _normalize_evidence(
    raw_items: object,
    field: str,
    id_prefix: str,
    warnings: list[str],
) -> tuple[OkfEvidence, ...]:
    normalized: list[OkfEvidence] = []
    for index, value in enumerate(_as_sequence(raw_items, field)):
        item = dict(_as_mapping(value, f"{field}[{index}]"))
        criterion = item.get("criterio_atacado")
        item["source_criterion_atacado"] = str(criterion)
        item["normalization_rule"] = None
        if criterion not in VALID_CRITERIOS:
            warnings.append(
                f"{field}[{index}].criterio_atacado: {criterion} normalizado a CRIT_OTRO"
            )
            item["criterio_atacado"] = "CRIT_OTRO"
            item["normalization_rule"] = "invalid_criterion_fallback"
        item["id"] = stable_id(
            id_prefix,
            str(item.get("subcategoria") or "prueba"),
            {
                key: item.get(key)
                for key in ("categoria", "subcategoria", "detalle", "objetivo_probatorio")
            },
        )
        normalized.append(
            OkfEvidence.model_validate({key: item[key] for key in OkfEvidence.model_fields})
        )
    return tuple(normalized)


def normalize_judgment(raw: Mapping[str, object]) -> OkfJudgment:
    """Valida y normaliza un registro sin añadir conclusiones jurídicas."""

    identifiers = _as_mapping(raw.get("identificadores"), "identificadores")
    burden = _as_mapping(raw.get("carga_prueba"), "carga_prueba")
    warnings: list[str] = []
    alleged_country = _text(raw, "pais_alegado_residencia_pf")
    countries = tuple(
        dict.fromkeys(
            country
            for country in ("España", alleged_country)
            if country.upper() not in _MISSING_VALUES
        )
    )
    source_file = _text(raw, "archivo")
    pruebas_aeat = _normalize_evidence(
        raw.get("Pruebas_AEAT"),
        "Pruebas_AEAT",
        "prueba-aeat",
        warnings,
    )
    pruebas_contribuyente = _normalize_evidence(
        raw.get("Pruebas_contribuyente"),
        "Pruebas_contribuyente",
        "prueba-contribuyente",
        warnings,
    )
    return OkfJudgment(
        archivo=source_file,
        slug=slugify(Path(source_file).stem),
        title=_text(identifiers, "ROJ"),
        roj=_text(identifiers, "ROJ"),
        ecli=_text(identifiers, "ECLI"),
        organo=_text(raw, "organo"),
        fecha_resolucion=_text(raw, "fecha_resolucion"),
        es_caso_residencia_irpf=_text(raw, "es_caso_residencia_irpf") == "SI",
        ejercicios_afectados=tuple(
            int(year)
            for year in re.findall(r"\b(?:19|20)\d{2}\b", _text(raw, "ejercicios_afectados"))
        ),
        paises=countries,
        pais_alegado_residencia_pf=alleged_country,
        pais_cdi_aplicado=_text(raw, "pais_CDI_aplicado"),
        se_invoca_cdi=_text(raw, "se_invoca_CDI") == "SI",
        tiebreaker_paso_decisivo=_text(raw, "tiebreaker_paso_decisivo"),
        criterios_detectados=tuple(
            str(value)
            for value in _as_sequence(
                raw.get("Criterios_residencia_detectados"),
                "Criterios_residencia_detectados",
            )
        ),
        criterios_decisivos=tuple(
            str(value) for value in _as_sequence(raw.get("Criterio_decisivo"), "Criterio_decisivo")
        ),
        resumen_criterios=_text(raw, "resumen_criterios"),
        doctrina_citada=tuple(
            str(value) for value in _as_sequence(raw.get("doctrina_citada"), "doctrina_citada")
        ),
        carga_prueba=OkfBurdenOfProof(
            quien_tenia_carga=_text(burden, "quien_tenia_carga"),
            motivo=_text(burden, "motivo"),
            cumplida=_text(burden, "cumplida"),
        ),
        razonamiento_residencia=_text(raw, "razonamiento_residencia"),
        pruebas_aeat=pruebas_aeat,
        pruebas_contribuyente=pruebas_contribuyente,
        resultado_final=_text(raw, "resultado_final"),
        citas=extract_nested_citations(raw, pruebas_aeat, pruebas_contribuyente),
        confianza_extraccion=_text(raw, "confianza_extraccion"),
        warnings=tuple(warnings),
    )
