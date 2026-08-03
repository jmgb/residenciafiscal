from __future__ import annotations

import hashlib
import json

import pytest

from deep_research_codex_runtime import (
    BudgetExceeded,
    BudgetTracker,
    RuntimeBudgets,
    codex_command,
    normalize_openai_usage,
    parse_codex_events,
    runtime_schema_path,
)
from deep_research_corpus import CorpusRepository
from deep_research_corpus_mcp import dispatch_tool
from deep_research_verifier import finalize_deep_research_output, load_model_pricing


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_pages_sha256(pages: list[dict[str, object]]) -> str:
    payload = json.dumps(
        pages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bundle(tmp_path):
    root = tmp_path / "rollout-106" / "2"
    (root / "retrieval").mkdir(parents=True)
    (root / "cases").mkdir()
    (root / "verbatim").mkdir()
    (root / "metadata").mkdir()
    (root / "metadata" / "rollout-manifest.json").write_text(
        json.dumps({"documents": [{"judgment_id": "san-1-2020", "source_sha256": "a" * 64}]}),
        encoding="utf-8",
    )
    (root / "metadata" / "model-pricing.json").write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-model-pricing/1",
                "catalog_version": "test-catalog",
                "model": "gpt-5.6-luna",
                "input_usd_per_mtok": "0.20",
                "output_usd_per_mtok": "1.20",
            }
        ),
        encoding="utf-8",
    )
    (root / "retrieval" / "rollout-106.corpus.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "judgment_id": "san-1-2020",
                        "search_text": "centro de intereses económicos y carga de la prueba",
                        "issue": {"issue_id": "centro-intereses", "question": "¿Dónde radica?"},
                        "holding": {"conclusion": "Radica en España"},
                        "facets": {"tax_years": [2020], "countries": ["España"]},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "cases" / "san-1-2020.case.json").write_text(
        json.dumps({"judgment": {"judgment_id": "san-1-2020"}, "facts": ["hecho"]}),
        encoding="utf-8",
    )
    raw_page_text = "La residencia exige prueba exacta."
    pages = [
        {
            "page_index": 1,
            "printed_page": "1",
            "raw_page_text": raw_page_text,
            "text_sha256": _sha256_text(raw_page_text),
            "extraction_status": "TEXT_EXTRACTED",
        }
    ]
    (root / "verbatim" / "san-1-2020.pages.json").write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-verbatim/1",
                "document_id": "san-1-2020",
                "source_file": "sentencias/SAN_1_2020.pdf",
                "source_sha256": "a" * 64,
                "extractor": {"name": "pypdf", "version": "6.14.2"},
                "page_count": 1,
                "pages_sha256": _canonical_pages_sha256(pages),
                "status": "COMPLETE",
                "pages": pages,
            }
        ),
        encoding="utf-8",
    )
    return root


def _draft(text="Texto paralelo no verificado."):
    return json.dumps(
        {
            "status": "completa",
            "text": text,
            "limits": [],
            "claims": [{"text": "La residencia exige prueba exacta.", "evidence_indexes": [1]}],
            "evidence": [
                {
                    "judgment_id": "san-1-2020",
                    "page": 1,
                    "source_sha256": "a" * 64,
                    "quote": "La residencia exige prueba exacta.",
                    "verification": "EXACT",
                }
            ],
        },
        ensure_ascii=False,
    )


def _audit():
    return [
        {
            "type": "mcp_tool_call",
            "server": "corpus",
            "tool": "search_corpus",
            "status": "completed",
        },
        {
            "type": "mcp_tool_call",
            "server": "corpus",
            "tool": "read_verbatim_page",
            "status": "completed",
        },
    ]


def test_runtime_command_has_only_corpus_tools_and_receives_request_over_stdin(tmp_path):
    command = codex_command(
        codex_bin="/usr/local/bin/codex",
        model="gpt-5.6-luna",
        reasoning_effort="high",
        schema_path=tmp_path / "schema.json",
        mcp_path=tmp_path / "mcp.py",
        bundle_path=tmp_path / "bundle",
    )
    assert command[-1] == "-"
    assert command[command.index("--model") + 1] == "gpt-5.6-luna"
    joined = "\n".join(command)
    assert 'model_reasoning_effort="high"' in joined
    assert 'web_search="disabled"' in joined
    assert "features.shell_tool=false" in joined
    assert "features.skill_search=false" in joined
    assert (
        'mcp_servers.corpus.enabled_tools=["search_corpus","read_case","read_verbatim_page"]'
        in joined
    )


def test_runtime_resolves_schema_inside_its_immutable_release(tmp_path):
    release = tmp_path / "runtime" / "releases" / "abc123"
    runtime = release / "deep_research_codex_runtime.py"

    assert runtime_schema_path(runtime) == release / "output.schema.json"


def test_finalizer_derives_visible_text_only_from_verified_claims_and_normalizes_cost(tmp_path):
    final = finalize_deep_research_output(
        _draft(),
        job_id="deep-job-1",
        bundle_path=_bundle(tmp_path),
        model="gpt-5.6-luna",
        reasoning_effort="high",
        latency_ms=123,
        usage={"input_tokens": 80, "cache_read_input_tokens": 20, "output_tokens": 50},
        tool_audit=_audit(),
    )

    assert final["text"] == "La residencia exige prueba exacta."
    assert "Texto paralelo" not in final["text"]
    assert final["cost_microusd"] == 80
    assert final["pricing_version"] == "test-catalog"
    assert final["model"] == "gpt-5.6-luna"
    assert final["reasoning_effort"] == "high"


def test_finalizer_trims_only_exterior_whitespace_before_exact_evidence_checks(tmp_path):
    draft = json.loads(_draft())
    draft["claims"][0]["text"] = "\n  La residencia exige prueba exacta. \t"
    draft["evidence"][0]["quote"] = "\n  La residencia exige prueba exacta. \t"

    final = finalize_deep_research_output(
        json.dumps(draft, ensure_ascii=False),
        job_id="deep-job-1",
        bundle_path=_bundle(tmp_path),
        model="gpt-5.6-luna",
        reasoning_effort="high",
        latency_ms=1,
        usage=None,
        tool_audit=_audit(),
    )

    assert final["text"] == "La residencia exige prueba exacta."
    assert final["claims"][0]["text"] == "La residencia exige prueba exacta."
    assert final["evidence"][0]["quote"] == "La residencia exige prueba exacta."


def test_finalizer_does_not_normalize_internal_evidence_whitespace(tmp_path):
    draft = json.loads(_draft())
    draft["claims"][0]["text"] = "La residencia exige  prueba exacta."
    draft["evidence"][0]["quote"] = "La residencia exige  prueba exacta."

    with pytest.raises(ValueError, match="exact raw_page_text substring"):
        finalize_deep_research_output(
            json.dumps(draft, ensure_ascii=False),
            job_id="deep-job-1",
            bundle_path=_bundle(tmp_path),
            model="gpt-5.6-luna",
            reasoning_effort="high",
            latency_ms=1,
            usage=None,
            tool_audit=_audit(),
        )


def test_finalizer_rejects_duplicate_evidence_indexes(tmp_path):
    draft = json.loads(_draft())
    draft["claims"][0]["evidence_indexes"] = [1, 1]

    with pytest.raises(ValueError, match="each claim requires evidence"):
        finalize_deep_research_output(
            json.dumps(draft),
            job_id="deep-job-1",
            bundle_path=_bundle(tmp_path),
            model="gpt-5.6-luna",
            reasoning_effort="high",
            latency_ms=1,
            usage=None,
            tool_audit=_audit(),
        )


def test_openai_usage_subtracts_cached_tokens_from_base_input():
    usage = normalize_openai_usage(
        {"input_tokens": 100, "cached_input_tokens": 20, "output_tokens": 50}
    )

    assert usage == {
        "input_tokens": 80,
        "cache_read_input_tokens": 20,
        "output_tokens": 50,
        "total_tokens": 150,
    }


def test_parser_rejects_and_audits_any_non_corpus_execution(tmp_path):
    stdout = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "command_execution", "status": "completed"},
                }
            ),
            json.dumps(
                {"type": "item.completed", "item": {"type": "agent_message", "text": _draft()}}
            ),
        ]
    )

    _session, _draft_text, _usage, audit = parse_codex_events(stdout)
    with pytest.raises(ValueError, match="unexpected call"):
        finalize_deep_research_output(
            _draft(),
            job_id="deep-job-1",
            bundle_path=_bundle(tmp_path),
            model="gpt-5.6-luna",
            reasoning_effort="high",
            latency_ms=1,
            usage=None,
            tool_audit=audit,
        )


def test_finalizer_rejects_whitespace_and_non_extractive_claims(tmp_path):
    bundle = _bundle(tmp_path)
    unsupported = json.loads(_draft())
    unsupported["claims"][0]["text"] = "La Luna es de queso."
    with pytest.raises(ValueError, match="literal evidence quote"):
        finalize_deep_research_output(
            json.dumps(unsupported),
            job_id="deep-job-1",
            bundle_path=bundle,
            model="gpt-5.6-luna",
            reasoning_effort="high",
            latency_ms=1,
            usage=None,
            tool_audit=_audit(),
        )

    whitespace = json.loads(_draft())
    whitespace["claims"][0]["text"] = " " * 20
    whitespace["evidence"][0]["quote"] = " " * 20
    with pytest.raises(ValueError, match="invalid claim text|evidence literal"):
        finalize_deep_research_output(
            json.dumps(whitespace),
            job_id="deep-job-1",
            bundle_path=bundle,
            model="gpt-5.6-luna",
            reasoning_effort="high",
            latency_ms=1,
            usage=None,
            tool_audit=_audit(),
        )


def test_finalizer_binds_verbatim_document_and_hash_to_rollout_manifest(tmp_path):
    bundle = _bundle(tmp_path)
    verbatim = bundle / "verbatim/san-1-2020.pages.json"
    document = json.loads(verbatim.read_text("utf-8"))
    document["source_sha256"] = "b" * 64
    verbatim.write_text(json.dumps(document), encoding="utf-8")
    draft = json.loads(_draft())
    draft["evidence"][0]["source_sha256"] = "b" * 64

    with pytest.raises(ValueError, match="rollout manifest"):
        finalize_deep_research_output(
            json.dumps(draft),
            job_id="deep-job-1",
            bundle_path=bundle,
            model="gpt-5.6-luna",
            reasoning_effort="high",
            latency_ms=1,
            usage=None,
            tool_audit=_audit(),
        )


def test_finalizer_rejects_verbatim_whose_internal_hashes_do_not_match(tmp_path):
    bundle = _bundle(tmp_path)
    verbatim = bundle / "verbatim/san-1-2020.pages.json"
    document = json.loads(verbatim.read_text("utf-8"))
    document["pages"][0]["raw_page_text"] = "La residencia exige prueba exacta. Alterado."
    verbatim.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="verbatim integrity"):
        finalize_deep_research_output(
            _draft(),
            job_id="deep-job-1",
            bundle_path=bundle,
            model="gpt-5.6-luna",
            reasoning_effort="high",
            latency_ms=1,
            usage=None,
            tool_audit=_audit(),
        )


@pytest.mark.parametrize("status", ["pregunta", "abstención", "error"])
def test_finalizer_replaces_all_non_substantive_model_prose_with_safe_templates(tmp_path, status):
    draft = {
        "status": status,
        "text": "Conclusión jurídica inventada por el modelo.",
        "limits": ["Otra conclusión jurídica inventada."],
        "claims": [],
        "evidence": [],
    }

    final = finalize_deep_research_output(
        json.dumps(draft, ensure_ascii=False),
        job_id="deep-job-1",
        bundle_path=_bundle(tmp_path),
        model="gpt-5.6-luna",
        reasoning_effort="high",
        latency_ms=1,
        usage=None,
        tool_audit=[],
    )

    assert "inventada" not in final["text"]
    assert final["limits"] == []


def test_finalizer_replaces_substantive_limits_with_deterministic_metadata(tmp_path):
    draft = json.loads(_draft())
    draft["status"] = "parcial"
    draft["limits"] = ["Conclusión jurídica no respaldada."]

    final = finalize_deep_research_output(
        json.dumps(draft, ensure_ascii=False),
        job_id="deep-job-1",
        bundle_path=_bundle(tmp_path),
        model="gpt-5.6-luna",
        reasoning_effort="high",
        latency_ms=1,
        usage=None,
        tool_audit=_audit(),
    )

    assert final["limits"] == [
        "Resultado parcial: el corpus no aporta evidencia para cubrir toda la consulta."
    ]
    assert "respaldada" not in final["limits"][0]


@pytest.mark.parametrize("usage", [{}, {"total_tokens": 0}, {"input_tokens": 0}])
def test_finalizer_treats_empty_or_zero_usage_as_unavailable(tmp_path, usage):
    final = finalize_deep_research_output(
        _draft(),
        job_id="deep-job-1",
        bundle_path=_bundle(tmp_path),
        model="gpt-5.6-luna",
        reasoning_effort="high",
        latency_ms=1,
        usage=usage,
        tool_audit=_audit(),
    )

    assert final["cost_microusd"] is None
    assert final["cost_measurement"] == "UNAVAILABLE"


def test_corpus_rejects_queries_without_searchable_tokens(tmp_path):
    repository = CorpusRepository(_bundle(tmp_path))

    for query in ("a", "UE"):
        with pytest.raises(ValueError, match="searchable token"):
            repository.search(query)


def test_mcp_exposes_case_and_verbatim_reads_but_no_generic_file_access(tmp_path):
    repository = CorpusRepository(_bundle(tmp_path))

    assert dispatch_tool(repository, "read_case", {"judgment_id": "san-1-2020"})["facts"] == [
        "hecho"
    ]
    page = dispatch_tool(
        repository,
        "read_verbatim_page",
        {"judgment_id": "san-1-2020", "page": 1},
    )
    assert page["raw_page_text"] == "La residencia exige prueba exacta."
    with pytest.raises(ValueError, match="unsupported"):
        dispatch_tool(repository, "read_file", {"path": "/etc/passwd"})


def test_runtime_budget_tracker_stops_excessive_tool_and_resource_reads(tmp_path):
    tracker = BudgetTracker(
        RuntimeBudgets(
            max_turns=2,
            max_tool_calls=2,
            max_documents=1,
            max_pages=1,
            max_cost_microusd=10_000,
        ),
        pricing=load_model_pricing(_bundle(tmp_path), "gpt-5.6-luna"),
    )
    tracker.observe(
        {
            "type": "item.started",
            "item": {
                "id": "call-1",
                "type": "mcp_tool_call",
                "server": "corpus",
                "tool": "read_verbatim_page",
                "arguments": {"judgment_id": "san-1-2020", "page": 1},
            },
        }
    )
    # Completion for the same call must not consume the budget twice.
    tracker.observe(
        {
            "type": "item.completed",
            "item": {
                "id": "call-1",
                "type": "mcp_tool_call",
                "server": "corpus",
                "tool": "read_verbatim_page",
                "arguments": {"judgment_id": "san-1-2020", "page": 1},
            },
        }
    )
    tracker.observe(
        {
            "type": "item.started",
            "item": {
                "id": "call-2",
                "type": "mcp_tool_call",
                "server": "corpus",
                "tool": "read_case",
                "arguments": {"judgment_id": "san-1-2020"},
            },
        }
    )

    with pytest.raises(BudgetExceeded, match="max_tool_calls"):
        tracker.observe(
            {
                "type": "item.started",
                "item": {
                    "id": "call-3",
                    "type": "mcp_tool_call",
                    "server": "corpus",
                    "tool": "search_corpus",
                    "arguments": {"query": "residencia fiscal"},
                },
            }
        )


def test_runtime_budget_tracker_stops_cost_as_soon_as_usage_is_reported(tmp_path):
    tracker = BudgetTracker(
        RuntimeBudgets(
            max_turns=2,
            max_tool_calls=10,
            max_documents=5,
            max_pages=5,
            max_cost_microusd=100,
        ),
        pricing=load_model_pricing(_bundle(tmp_path), "gpt-5.6-luna"),
    )

    with pytest.raises(BudgetExceeded, match="max_cost_microusd"):
        tracker.observe(
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 1_000, "output_tokens": 1_000},
            }
        )


def test_draft_schema_worst_case_fits_callback_envelope():
    schema = json.loads(
        (
            __import__("pathlib").Path(__file__).parents[1]
            / "schemas/residenciafiscal-deep-research-draft-v2.schema.json"
        ).read_text("utf-8")
    )
    properties = schema["properties"]
    claim = properties["claims"]["items"]["properties"]
    evidence = properties["evidence"]["items"]["properties"]
    limits = properties["limits"]
    unicode_char = "💥"
    claims = [
        {
            "text": unicode_char * claim["text"]["maxLength"],
            "evidence_indexes": [1],
        }
        for _ in range(properties["claims"]["maxItems"])
    ]
    items = [
        {
            "judgment_id": "san-1-2020",
            "page": 1,
            "source_sha256": "a" * 64,
            "quote": unicode_char * evidence["quote"]["maxLength"],
            "verification": "EXACT",
        }
        for _ in range(properties["evidence"]["maxItems"])
    ]
    final = {
        "schema_version": "residenciafiscal-deep-research-output/2",
        "job_id": "deep-job-1",
        "request_id": "deep-job-1",
        "status": "completa",
        "text": "\n\n".join(item["text"] for item in claims),
        "limits": [unicode_char * limits["items"]["maxLength"] for _ in range(limits["maxItems"])],
        "claims": claims,
        "evidence": items,
        "cost_microusd": 1,
        "cost_measurement": "ESTIMATED",
        "pricing_version": "test-catalog",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "high",
        "latency_ms": 1,
    }
    final_text = json.dumps(final, ensure_ascii=False, separators=(",", ":"))
    callback = json.dumps({"job_id": "deep-job-1", "status": "completed", "final_text": final_text})

    assert len(callback.encode("utf-8")) <= 250_000


def test_draft_schema_avoids_codex_unsupported_unique_items_keyword():
    schema = json.loads(
        (
            __import__("pathlib").Path(__file__).parents[1]
            / "schemas/residenciafiscal-deep-research-draft-v2.schema.json"
        ).read_text("utf-8")
    )

    def contains_unique_items(value):
        if isinstance(value, dict):
            return "uniqueItems" in value or any(
                contains_unique_items(item) for item in value.values()
            )
        if isinstance(value, list):
            return any(contains_unique_items(item) for item in value)
        return False

    assert not contains_unique_items(schema)
