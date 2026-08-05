"""Garantías del borrador de A que ningún proveedor da por nosotros.

Aquí no se comprueba el modo estricto de OpenAI. Eso lo normaliza el paquete
desde la v0.7.0 (`providers/strict_schema.py`), y reimplementar sus reglas
recursivas en este repositorio solo crearía una copia que diverge en silencio.

Lo que queda es de dominio: que una respuesta jurídica no pueda callar sus
salvedades ni su evidencia, y que las instrucciones pidan lo que el contrato
exige.
"""

from __future__ import annotations

from chat_answer_contract import ChatAnswerDraft, StructuredChatAnswerDraft


def test_las_salvedades_y_la_evidencia_son_obligatorias() -> None:
    """Callar no puede significar «no hay».

    Con valor por defecto, un `limits` omitido se convertía en tupla vacía y una
    respuesta sin reservas declaradas era indistinguible de otra en la que el
    modelo no se pronunció.
    """
    obligatorios = set(StructuredChatAnswerDraft.model_json_schema()["required"])

    assert {"limits", "claims"} <= obligatorios

    claim_schema = StructuredChatAnswerDraft.model_json_schema()["$defs"]["StructuredClaim"]
    assert {"kind", "text", "evidence_ids"} <= set(claim_schema["required"])


def test_los_prompts_declaran_la_version_que_se_persiste() -> None:
    """Etiquetar una fila con una versión y enviar otro texto falsea el experimento.

    La versión de prompt viaja a Supabase por petición y decide con qué se
    comparan las métricas. Si el texto no es el que la etiqueta nombra, las dos
    ejecuciones dejan de ser comparables sin que nada avise.
    """
    from chat_answer_prompt import (
        FILE_SEARCH_ANSWER_INSTRUCTIONS,
        FILE_SEARCH_PROMPT_VERSION,
        STRUCTURED_ANSWER_INSTRUCTIONS,
        STRUCTURED_PROMPT_VERSION,
    )

    assert STRUCTURED_PROMPT_VERSION == "structured-claims-v5"
    assert FILE_SEARCH_PROMPT_VERSION == "file-search-authority-v8"
    # Las reglas que el baseline F0.2 midió y que distinguen v8 de un prompt
    # genérico: si desaparecen, la etiqueta deja de describir el texto.
    for regla in (
        "No atribuyas al tribunal argumentos de las partes",
        "ausencias esporádicas",
        "no conviertas la prueba o el resultado de un caso concreto en una regla general".lower(),
    ):
        assert regla.lower() in FILE_SEARCH_ANSWER_INSTRUCTIONS.lower()
    for regla in (
        "claims",
        "afirmaciones jurídicas atómicas",
        "judgment_id",
        "judicial_assessment",
        "No relegues una insuficiencia probatoria decisiva",
    ):
        assert regla.lower() in STRUCTURED_ANSWER_INSTRUCTIONS.lower()


def test_las_pistas_terminologicas_solo_aparecen_cuando_procede() -> None:
    from chat_answer_prompt import retrieval_hints

    assert "gimnasios" in retrieval_hints("¿Sirve la cuota del gym como prueba?")
    assert "geolocalización" in retrieval_hints("¿Y el teléfono móvil?")
    assert retrieval_hints("¿Qué son las ausencias esporádicas?") == ""


def test_el_prompt_pide_los_campos_que_el_contrato_exige() -> None:
    """Exigir en el esquema lo que las instrucciones callan es una trampa.

    El modelo no ve el contrato: si se le obliga a emitir un campo que el prompt
    nunca menciona, el fallo aparece en producción y se atribuye al modelo.
    """
    from chat_answer_prompt import STRUCTURED_ANSWER_INSTRUCTIONS

    obligatorios = set(StructuredChatAnswerDraft.model_json_schema()["required"])
    sin_mencionar = sorted(
        campo
        for campo in obligatorios
        if campo not in STRUCTURED_ANSWER_INSTRUCTIONS and campo not in {"status", "answer"}
    )

    assert sin_mencionar == [], (
        f"el contrato exige {sin_mencionar} pero las instrucciones no los piden"
    )


def test_la_estrategia_b_conserva_su_tolerancia() -> None:
    """B corre contra File Search y alimenta artefactos de revisión ya generados.

    Endurecer la clase base convertiría en fallo respuestas hoy válidas.
    """
    assert "limits" not in set(ChatAnswerDraft.model_json_schema().get("required", []))
