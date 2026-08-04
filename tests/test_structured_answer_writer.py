from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any


def _claim_from_quote(quote: str) -> str:
    """Afirmación que sí comparte vocabulario con su extracto.

    El gate de relevancia compara términos de la claim con los de sus citas; un
    texto inventado se retiraría, que es justo lo que debe pasar en producción.
    """
    return " ".join(quote.split()[:20])


class RecordingWriter:
    def __init__(
        self,
        *,
        evidence_ids: tuple[str, ...] = ("E1",),
        status: str = "completa",
        unrelated_claim: bool = False,
    ) -> None:
        self.evidence_ids = evidence_ids
        self.status = status
        self.unrelated_claim = unrelated_claim
        self.requests: list[Any] = []

    async def write(self, request: Any) -> Any:
        from llm_gateway import Cost, CostMeasurement

        from chat_answer_contract import StructuredChatAnswerDraft, StructuredClaim
        from structured_answer_writer import ChatWriterResult, ChatWriterUsage

        self.requests.append(request)
        quotes = {
            item["evidence_id"]: item["quote"]
            for item in json.loads(request.evidence_context)["evidence"]
        }
        claims = tuple(
            StructuredClaim(
                text=_claim_from_quote(quotes.get(evidence_id, ""))
                or "Afirmación redactada sin ningún respaldo literal comprobable.",
                evidence_ids=(evidence_id,),
            )
            for evidence_id in self.evidence_ids
        )
        if self.unrelated_claim:
            claims = (
                *claims,
                StructuredClaim(
                    text="Zanahorias bicicletas taxonomías inventadas completamente ajenas.",
                    evidence_ids=(self.evidence_ids[0],),
                ),
            )
        return ChatWriterResult(
            draft=StructuredChatAnswerDraft(
                status=self.status,
                limits=(),
                claims=claims,
            ),
            usage=ChatWriterUsage(
                input_tokens=120,
                output_tokens=30,
                usage_complete=True,
            ),
            model_used=request.model,
            # El importe lo mide el gateway, así que el doble lo aporta. Que el
            # test tenga que darlo es la prueba de que la estrategia ya no lo
            # recalcula a partir de tokens y tarifas.
            cost=Cost(
                measurement=CostMeasurement.ACTUAL,
                microusd=60,
                pricing_version="2026-07-31",
            ),
        )


def _corpus() -> Any:
    from jurisprudence_retrieval_corpus import load_retrieval_corpus

    return load_retrieval_corpus(
        Path("knowledge/jurisprudencia-v3/retrieval/corpus.json").read_bytes()
    )


async def test_redactor_recibe_evidencias_opacas_y_solo_publica_las_usadas() -> None:
    from current_structured_strategy import CurrentStructuredStrategy

    writer = RecordingWriter(evidence_ids=("E1", "E3"))
    result = await CurrentStructuredStrategy(_corpus(), writer=writer).answer(
        "¿Qué tiene en cuenta Hacienda para demostrar la residencia fiscal en España?",
        request_id="req-writer",
    )

    assert result.strategy == "current_structured"
    assert result.status == "completa"
    assert len(result.sources) == 2
    # Cada afirmación enlaza sus propias citas: una sola claim con toda la
    # respuesta y todas las fuentes afirmaría un respaldo que nadie comprobó.
    assert [claim.source_indexes for claim in result.claims] == [(1,), (2,)]
    assert result.text.splitlines() == [
        f"- {claim.text} [{claim.source_indexes[0]}]" for claim in result.claims
    ]
    from chat_model_policy import CHAT_MODEL, CHAT_REASONING_EFFORT

    assert all(source.verification == "EXACT" for source in result.sources)
    # 120 de entrada y 30 de salida a la tarifa de Luna (0,20 y 1,20 USD/Mtok),
    # que es el modelo de A desde que dejó de heredar el de File Search.
    assert result.cost.amount_usd == Decimal("0.000060")
    assert result.cost.input_tokens == 120
    assert result.cost.output_tokens == 30
    assert result.model == CHAT_MODEL

    request = writer.requests[0]
    assert request.model == CHAT_MODEL
    # El esfuerzo viaja con la petición: sin él, declarar `max` en la política
    # no cambiaría nada, porque saldría el valor por defecto del proveedor.
    assert request.reasoning_effort == CHAT_REASONING_EFFORT
    assert request.temperature == 0
    assert request.fallback_policy == "disabled"
    assert request.response_schema["title"] == "StructuredChatAnswerDraft"
    context = json.loads(request.evidence_context)
    assert len(context["evidence"]) <= 12
    assert len(request.evidence_context) < 40_000
    assert [item["evidence_id"] for item in context["evidence"]] == [
        f"E{index}" for index in range(1, len(context["evidence"]) + 1)
    ]
    assert {item["evidence_id"] for item in context["evidence"]} >= {"E1", "E3"}
    assert all(item["quote"] for item in context["evidence"])
    assert all(item["page"] > 0 for item in context["evidence"])
    assert {item["judgment_id"] for item in context["evidence"]} == {
        item["judgment_id"] for item in context["units"]
    }
    assert {item["role"] for item in context["evidence"]} == {
        "support",
        "contrast",
    }


async def test_referencia_desconocida_falla_cerrada_y_conserva_el_coste() -> None:
    from current_structured_strategy import CurrentStructuredStrategy

    result = await CurrentStructuredStrategy(
        _corpus(),
        writer=RecordingWriter(evidence_ids=("E999",)),
    ).answer(
        "¿Qué tiene en cuenta Hacienda para demostrar la residencia fiscal en España?",
        request_id="req-unknown-evidence",
    )

    assert result.status == "error"
    assert result.text == ""
    assert result.sources == ()
    # El fallo no borra el gasto: la llamada se pagó igual, a tarifa de Luna.
    assert result.cost.amount_usd == Decimal("0.000060")
    assert "E999" in result.limits[0]


async def test_respuesta_sustantiva_sin_evidencias_falla_cerrada() -> None:
    from current_structured_strategy import CurrentStructuredStrategy

    result = await CurrentStructuredStrategy(
        _corpus(),
        writer=RecordingWriter(evidence_ids=()),
    ).answer(
        "¿Qué tiene en cuenta Hacienda para demostrar la residencia fiscal en España?",
        request_id="req-no-evidence",
    )

    assert result.status == "error"
    assert result.text == ""
    assert result.sources == ()
    assert "ninguna evidencia" in result.limits[0]


async def test_abstencion_de_recuperacion_no_llama_al_llm_y_cuesta_cero() -> None:
    from current_structured_strategy import CurrentStructuredStrategy

    writer = RecordingWriter()
    result = await CurrentStructuredStrategy(_corpus(), writer=writer).answer(
        "¿Qué son las ausencias esporádicas y cuándo computan?",
        request_id="req-abstain",
    )

    assert result.status == "abstención"
    assert "no cubre" in result.text.casefold()
    assert "ausencias" in result.text.casefold()
    assert writer.requests == []
    assert result.cost.amount_usd == Decimal("0")
    assert result.model == "deterministic-structured-v3"


async def test_pregunta_de_recuperacion_pide_los_hechos_ausentes_sin_llm() -> None:
    from current_structured_strategy import CurrentStructuredStrategy

    writer = RecordingWriter()
    result = await CurrentStructuredStrategy(_corpus(), writer=writer).answer(
        "Digo que pasé menos de 183 días en España, ¿qué usaría Hacienda?",
        request_id="req-question",
    )

    assert result.status == "pregunta"
    assert "necesito" in result.text.casefold()
    assert "ejercicio" in result.text.casefold()
    assert "país" in result.text.casefold()
    assert writer.requests == []
    assert result.cost.amount_usd == Decimal("0")


async def test_una_afirmacion_sin_respaldo_literal_se_retira() -> None:
    from current_structured_strategy import CurrentStructuredStrategy

    result = await CurrentStructuredStrategy(
        _corpus(),
        writer=RecordingWriter(evidence_ids=("E1",), unrelated_claim=True),
    ).answer(
        "¿Qué tiene en cuenta Hacienda para demostrar la residencia fiscal en España?",
        request_id="req-irrelevant-claim",
    )

    assert len(result.claims) == 1
    assert "Zanahorias" not in result.text
    # Retirar una afirmación degrada la respuesta: publicarla como completa
    # ocultaría que parte de lo redactado no se pudo respaldar.
    assert result.status == "parcial"
    assert any("sin respaldo literal suficiente" in limit for limit in result.limits)


async def test_una_pregunta_por_el_supremo_declara_la_autoridad_indirecta() -> None:
    from current_structured_strategy import CurrentStructuredStrategy

    result = await CurrentStructuredStrategy(_corpus(), writer=RecordingWriter()).answer(
        "¿Qué prueba exige el Tribunal Supremo para acreditar la residencia fiscal en España?",
        request_id="req-authority",
    )

    assert result.diagnostics is not None
    assert result.diagnostics["authority_intent"] == "tribunal_supremo"
    if result.status != "error" and result.diagnostics["authority_match"] == "missing":
        assert any("Tribunal Supremo" in limit for limit in result.limits)
        assert result.status != "completa"


def test_contrato_comun_permite_citas_externas_de_file_search() -> None:
    from chat_answer_contract import ChatAnswerDraft, StructuredChatAnswerDraft

    draft = ChatAnswerDraft.model_validate(
        {
            "status": "parcial",
            "answer": "La muestra solo cubre parcialmente esta cuestión.",
            "limits": ["No consta un calendario completo."],
        }
    )

    assert "claims" not in draft.model_dump()
    assert "claims" not in ChatAnswerDraft.model_json_schema()["properties"]
    assert "claims" in StructuredChatAnswerDraft.model_json_schema()["properties"]
    # A ya no emite prosa libre: el texto público se compone desde las claims.
    assert "answer" not in StructuredChatAnswerDraft.model_json_schema()["properties"]
