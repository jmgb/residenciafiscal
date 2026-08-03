"""Contrato C0 para jobs y resultados de investigación profunda."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_un_job_aplica_limites_operativos_por_defecto() -> None:
    from deep_research_contracts import DeepResearchJob

    job = DeepResearchJob(
        schema_version="residenciafiscal-deep-research-job/1",
        job_id="job-2026-08-03-001",
        request_id="request-001",
        bundle_id="rollout-106/1",
        question="¿Qué pruebas valoró el tribunal?",
    )

    assert job.limits.timeout_ms == 180_000
    assert job.limits.max_turns == 12
    assert job.limits.max_tool_calls == 80
    assert job.limits.max_documents == 12
    assert job.limits.max_pages == 120
    assert job.limits.max_cost_microusd == 200_000


def test_un_job_rechaza_limites_fuera_de_la_politica() -> None:
    from deep_research_contracts import DeepResearchJob

    with pytest.raises(ValidationError):
        DeepResearchJob(
            schema_version="residenciafiscal-deep-research-job/1",
            job_id="job-1",
            request_id="request-1",
            bundle_id="rollout-106/1",
            question="Pregunta válida",
            limits={"timeout_ms": 999, "max_cost_microusd": 2_000_001},
        )


def test_el_resultado_exige_evidencia_tipada_y_no_expone_razonamiento() -> None:
    from deep_research_contracts import DeepResearchOutput

    result = DeepResearchOutput(
        schema_version="residenciafiscal-deep-research-output/1",
        job_id="job-1",
        request_id="request-1",
        status="completa",
        text="Respuesta respaldada.",
        limits=(),
        claims=({"text": "Afirmación.", "evidence_indexes": (1,)},),
        evidence=(
            {
                "judgment_id": "san-1210-2023",
                "page": 4,
                "source_sha256": "a" * 64,
                "quote": "Texto literal.",
                "verification": "EXACT",
            },
        ),
    )

    assert result.claims[0].evidence_indexes == (1,)
    assert "reasoning" not in DeepResearchOutput.model_fields
