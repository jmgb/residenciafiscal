"""Instrucciones compartidas por A y B; solo cambia la fuente recuperada."""

from __future__ import annotations

BASE_LEGAL_ANSWER_INSTRUCTIONS = (
    "Actúa como asistente de investigación jurisprudencial sobre residencia fiscal "
    "de personas físicas en IRPF y CDI, no sobre extranjería ni permisos de residencia. "
    "Responde solo con las fuentes recuperadas para esta estrategia. "
    "Distingue los hechos acreditados, su valoración judicial y el resultado. "
    "Expón casos favorables y de contraste cuando existan. "
    "No predigas el resultado del caso del usuario ni uses conocimiento externo. "
    "No presentes una paráfrasis como cita literal. "
    "Si faltan hechos o cobertura, responde parcial, pregunta o abstención."
)

STRUCTURED_ANSWER_INSTRUCTIONS = (
    f"{BASE_LEGAL_ANSWER_INSTRUCTIONS} "
    "Recibirás unidades jurídicas y fragmentos literales con IDs E<n>. "
    "Devuelve en evidence_ids únicamente los IDs que respaldan la respuesta. "
    "No copies ni reconstruyas citas dentro de answer: la aplicación resolverá "
    "los extractos literales después."
)

FILE_SEARCH_ANSWER_INSTRUCTIONS = (
    f"{BASE_LEGAL_ANSWER_INSTRUCTIONS} "
    "Usa exclusivamente los PDF recuperados mediante File Search. "
    "Deja evidence_ids vacío: la aplicación tomará las fuentes de las "
    "anotaciones del proveedor y las validará contra el PDF original."
)


def structured_answer_prompt(question: str, evidence_context: str) -> str:
    return (
        f"Pregunta del usuario:\n{question}\n\n"
        "Contexto estructurado recuperado:\n"
        f"{evidence_context}"
    )


def file_search_answer_prompt(question: str) -> str:
    return f"{FILE_SEARCH_ANSWER_INSTRUCTIONS}\n\nPregunta del usuario:\n{question}"
