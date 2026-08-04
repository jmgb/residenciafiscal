"""Análisis determinista y auditable de consultas para la fase D."""

from __future__ import annotations

import re
import unicodedata

from pydantic import Field

from jurisprudence_case_catalogs import (
    CriterionId,
    EvidenceCategory,
    JurisprudenceCaseModel,
)
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from jurisprudence_sample_evaluation_models import ResponseBehavior


class QueryAnalysis(JurisprudenceCaseModel):
    criterion_ids: tuple[CriterionId, ...]
    evidence_categories: tuple[EvidenceCategory, ...]
    countries: tuple[str, ...]
    tax_years: tuple[int, ...]
    is_personal_case: bool
    missing_facts: tuple[str, ...]
    uncovered_facets: tuple[str, ...]
    behavior: ResponseBehavior
    behavior_reasons: tuple[str, ...] = Field(min_length=1)


_FACETS = (
    (CriterionId.SPORADIC_ABSENCES, ("ausencias esporadicas",)),
    (
        CriterionId.DAYS_183,
        ("183", "dias", "calendario", "pasaporte", "billete", "reserva"),
    ),
    (
        CriterionId.ECONOMIC_INTERESTS,
        ("centro economico", "intereses economicos", "ingresos", "rentas", "sociedad", "consej"),
    ),
    (
        CriterionId.FAMILY_PRESUMPTION,
        ("familia", "pareja", "conyuge", "hijo", "presuncion familiar"),
    ),
    (
        CriterionId.TREATY_TIEBREAKER,
        ("convenio", "cdi", "dos paises", "ambos paises", "vivienda permanente"),
    ),
)
_EVIDENCE = (
    (EvidenceCategory.PHYSICAL_PRESENCE, ("dias", "pasaporte", "billete", "viaje", "reserva")),
    (EvidenceCategory.HOUSING, ("vivienda", "casa", "alquiler", "domicilio")),
    (
        EvidenceCategory.HOUSEHOLD_CONSUMPTION,
        ("electricidad", "agua", "gas", "gasoleo", "suministro", "paqueteria", "combustible"),
    ),
    (
        EvidenceCategory.FINANCIAL_CONSUMPTION,
        ("tarjeta", "pago", "retirada", "consumo", "movimiento"),
    ),
    (EvidenceCategory.FAMILY, ("familia", "pareja", "conyuge", "hijo")),
    (EvidenceCategory.HEALTH, ("salud", "medic", "discapacidad")),
    (
        EvidenceCategory.ECONOMIC_ACTIVITY,
        ("empleo", "trabajo", "sociedad", "consej", "ingresos", "rentas", "inversion"),
    ),
    (
        EvidenceCategory.FOREIGN_TAX_DOCUMENTATION,
        ("certificado", "documentacion extranjera", "residencia emitido", "declaracion"),
    ),
)
_PERSONAL = re.compile(
    r"\b(mi|mis|me|soy|estoy|estuve|vivo|resido|tengo|trabajo|gano|digo|aseguro)\b"
)
_FACT_DIMENSIONS = (
    ("ejercicio", ("ejercicio", "ano", "201", "202")),
    ("país o países implicados", ("francia", "suiza", "monaco", "portugal", "reino unido")),
    ("calendario de presencia", ("dias", "183", "170", "calendario")),
    ("familia", ("familia", "pareja", "conyuge", "hijo")),
    ("vivienda", ("vivienda", "casa", "domicilio", "alquiler")),
    ("actividad e ingresos", ("trabajo", "empleo", "ingresos", "rentas", "sociedad", "inversion")),
    ("documentación fiscal extranjera", ("certificado", "declaracion", "documentacion")),
)
_PARTIAL_PATTERNS = (
    "han rechazado",
    "no haya considerado suficientes",
    "calcularon los dias",
    "pasaporte",
    "tarjetas de embarque",
    "billetes",
    "quien debe probar",
    "carga de probar",
    "carga al contribuyente",
    "carga de desmentir",
    "centro economico estaba fuera",
    "tarjetas y retiradas",
    "tarjetas y otros consumos",
    "requisitos se exigieron",
    "contenido debe tener un certificado",
    "vivienda permanente en ambos",
    "interactuan cdi",
    "convenio y",
    "diferencia los casos con sancion",
    # El corpus habla de cuotas de clubs deportivos y de contratos de telefonía,
    # nunca de un uso que acredite presencia en una fecha. Publicar `completa`
    # sobre ese material afirmaría más de lo que el material sostiene.
    "gym",
    "gimnasio",
    "telefono movil",
)
_ASK_PATTERNS = (
    "se parece mas a mi",
    "parece mas a mi situacion",
    "dos paises me consideran",
    "espana y el otro estado dicen",
    "empleo extranjero e inversiones",
)
_DOMAIN_TERMS = (
    "residencia",
    "residente",
    "resido",
    "fiscal",
    "hacienda",
    "aeat",
    "tribunal",
    "prueba",
    "contribuyente",
    "irpf",
    "liquidacion",
    "sancion",
    "indicio",
    "sentencia",
    "caso",
    "fragmento",
    "pagina",
)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _matches(text: str, needles: tuple[str, ...]) -> bool:
    return any(item in text for item in needles)


def analyze_query(query: str, corpus: RetrievalCorpus) -> QueryAnalysis:
    """Extrae señales; las etiquetas del banco de evaluación no intervienen."""

    text = _fold(query)
    criteria = tuple(facet for facet, words in _FACETS if _matches(text, words))
    evidence = tuple(facet for facet, words in _EVIDENCE if _matches(text, words))
    countries = tuple(
        country
        for country in sorted(
            {country for unit in corpus.units for country in unit.facets.countries}
        )
        if _fold(country) in text
    )
    years = tuple(dict.fromkeys(int(item) for item in re.findall(r"\b(?:19|20)\d{2}\b", text)))
    personal = _PERSONAL.search(text) is not None
    missing = tuple(name for name, words in _FACT_DIMENSIONS if not _matches(text, words))
    covered_criteria = {item for unit in corpus.units for item in unit.facets.criterion_ids}
    uncovered = tuple(item.value for item in criteria if item not in covered_criteria)
    if not criteria and not evidence and not _matches(text, _DOMAIN_TERMS):
        uncovered = ("OUT_OF_SCOPE",)

    if uncovered:
        behavior: ResponseBehavior = "abstenerse"
        reasons = ("la consulta pide una faceta sin cobertura estructurada en el corpus",)
    elif _matches(text, _ASK_PATTERNS):
        behavior = "preguntar"
        reasons = ("la comparación individual necesita hechos adicionales",)
    elif _matches(text, _PARTIAL_PATTERNS):
        behavior = "parcial"
        reasons = ("la muestra permite contexto, pero no una regla general completa",)
    elif (
        personal
        and len(missing) >= 4
        and not _matches(
            text, ("automaticamente", "por si solo", "que sigue", "rebatir", "desvirtua")
        )
    ):
        behavior = "preguntar"
        reasons = ("el caso personal no contiene suficientes dimensiones comparables",)
    else:
        behavior = "responder"
        reasons = ("la consulta está cubierta por unidades y anclajes de la muestra",)

    return QueryAnalysis(
        criterion_ids=criteria,
        evidence_categories=evidence,
        countries=countries,
        tax_years=years,
        is_personal_case=personal,
        missing_facts=missing,
        uncovered_facets=uncovered,
        behavior=behavior,
        behavior_reasons=reasons,
    )
