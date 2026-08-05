"""Verificación determinista de la respuesta del perfil jurídico Codex."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

RESULT_SCHEMA = "residenciafiscal-deep-research-output/2"
ALLOWED_TOOLS = {"search_corpus", "read_case", "read_verbatim_page"}
_SAFE_JUDGMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_STATUSES = {"completa", "parcial", "pregunta", "abstención", "error"}
_DRAFT_KEYS = {"status", "text", "limits", "claims", "evidence"}
_MAX_TEXT_CHARS = 4_000
_MAX_LIMITS = 8
_MAX_LIMIT_CHARS = 200
_MAX_CLAIMS = 10
_MAX_CLAIM_CHARS = 400
_MAX_EVIDENCE = 12
_MAX_QUOTE_CHARS = 800
_MIN_CLAIM_GROUNDING_RATIO = 0.4
_COMPLETE_QUOTE_END = re.compile(r'[.!?](?:["”»’])?$')
_CLAIM_GROUNDING_STOPWORDS = {
    "acerca",
    "alcance",
    "breve",
    "como",
    "con",
    "consecuencia",
    "contra",
    "cual",
    "cuando",
    "debe",
    "del",
    "desde",
    "donde",
    "el",
    "ella",
    "entre",
    "esa",
    "ese",
    "esta",
    "este",
    "fiscal",
    "las",
    "limite",
    "los",
    "mediante",
    "para",
    "pero",
    "por",
    "puede",
    "que",
    "respuesta",
    "residencia",
    "ser",
    "sin",
    "sobre",
    "sus",
    "una",
    "uno",
}
_NEGATION_TERMS = {"ni", "no", "nunca", "sin", "tampoco"}
_REQUIRED_LITERAL_LEGAL_TERMS = {
    "183 dias",
    "ausencias esporadicas",
    "competente para gravar",
    "centro de intereses vitales",
    "decision unilateral",
    "derecho interno",
    "morada habitual",
    "nacionalidad",
    "nucleo de intereses economicos",
    "por si solo",
    "renta mundial",
    "vivienda permanente",
}
_VERBATIM_KEYS = {
    "schema_version",
    "document_id",
    "source_file",
    "source_sha256",
    "extractor",
    "page_count",
    "pages_sha256",
    "status",
    "pages",
}
_VERBATIM_PAGE_KEYS = {
    "page_index",
    "printed_page",
    "raw_page_text",
    "text_sha256",
    "extraction_status",
}
_NON_SUBSTANTIVE_TEXT = {
    "pregunta": "Necesito que concretes la cuestión jurídica o los hechos relevantes antes de buscar en el corpus.",
    "abstención": "No hay evidencia suficiente en el corpus de sentencias para responder a la consulta.",
    "error": "No se ha podido completar la investigación de forma verificable.",
}
_GENERIC_PARTIAL_LIMIT = (
    "Resultado parcial: el corpus no aporta evidencia para cubrir toda la consulta."
)
_UNMATCHED_QUOTE_LIMIT = (
    "Se descartó {count} cita que no coincide literalmente con su página del PDF.",
    "Se descartaron {count} citas que no coinciden literalmente con su página del PDF.",
)
_DROPPED_CLAIM_LIMIT = (
    "Se retiró {count} afirmación que quedó sin cita verificable.",
    "Se retiraron {count} afirmaciones que quedaron sin cita verificable.",
)
_PRICING_KEYS = {
    "schema_version",
    "catalog_version",
    "model",
    "input_usd_per_mtok",
    "output_usd_per_mtok",
}


@dataclass(frozen=True)
class ModelPricing:
    catalog_version: str
    model: str
    input_microusd_per_token: Decimal
    output_microusd_per_token: Decimal


class UnmatchedEvidenceQuote(ValueError):
    """A model quote that cannot be localized uniquely in its declared page."""


@dataclass(frozen=True)
class _GraphOutcome:
    """Lo que el verificador retiró del borrador, contado por causa.

    Las cifras son hechos constatados por Python, no prosa del modelo, así que
    pueden publicarse en `limits` sin abrir el canal libre que el contrato cierra.
    """

    unmatched_quotes: int
    dropped_claims: int

    def limits(self) -> list[str]:
        lines = []
        if self.unmatched_quotes:
            lines.append(_plural_limit(self.unmatched_quotes, _UNMATCHED_QUOTE_LIMIT))
        if self.dropped_claims:
            lines.append(_plural_limit(self.dropped_claims, _DROPPED_CLAIM_LIMIT))
        return lines


def load_model_pricing(bundle_path: Path, model: str) -> ModelPricing:
    path = (bundle_path.resolve() / "metadata/model-pricing.json").resolve()
    if not path.is_relative_to(bundle_path.resolve()):
        raise ValueError("model pricing path escapes bundle")
    try:
        document = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("versioned model pricing is unavailable") from exc
    if (
        not isinstance(document, dict)
        or set(document) != _PRICING_KEYS
        or document.get("schema_version") != "residenciafiscal-model-pricing/1"
        or document.get("model") != model
        or not isinstance(document.get("catalog_version"), str)
        or not document["catalog_version"].strip()
    ):
        raise ValueError("versioned model pricing is invalid")
    try:
        input_rate = Decimal(document["input_usd_per_mtok"])
        output_rate = Decimal(document["output_usd_per_mtok"])
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("versioned model pricing is invalid") from exc
    if (
        not input_rate.is_finite()
        or not output_rate.is_finite()
        or input_rate < 0
        or output_rate < 0
    ):
        raise ValueError("versioned model pricing is invalid")
    return ModelPricing(
        catalog_version=document["catalog_version"],
        model=model,
        input_microusd_per_token=input_rate,
        output_microusd_per_token=output_rate,
    )


def finalize_deep_research_output(
    draft_text: str,
    *,
    job_id: str,
    bundle_path: Path,
    model: str,
    reasoning_effort: str,
    latency_ms: int,
    usage: dict[str, int] | None,
    tool_audit: list[dict[str, str]] | None,
) -> dict[str, Any]:
    draft = _parse_draft(draft_text)
    _trim_exterior_evidence_whitespace(draft)
    _verify_tool_audit(draft["status"], tool_audit)
    outcome = _verify_evidence_graph(draft, bundle_path.resolve())
    pricing = load_model_pricing(bundle_path, model)
    cost_microusd = estimated_cost_microusd(usage, pricing)
    cost_measurement = "ESTIMATED" if cost_microusd is not None else "UNAVAILABLE"
    verified_text = _verified_text(draft)
    return {
        "schema_version": RESULT_SCHEMA,
        "job_id": job_id,
        "request_id": job_id,
        **draft,
        # Never trust a parallel prose channel. The visible answer is derived
        # exclusively from claims that participate in the verified graph.
        "text": verified_text,
        "limits": _verified_limits(draft["status"], outcome),
        "cost_microusd": cost_microusd,
        "cost_measurement": cost_measurement,
        "pricing_version": pricing.catalog_version,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "latency_ms": max(0, latency_ms),
    }


def _trim_exterior_evidence_whitespace(draft: dict[str, Any]) -> None:
    """Canonicalize harmless model formatting before strict corpus checks.

    Internal whitespace remains untouched: every normalized quote must still be
    an exact substring of the immutable verbatim page.
    """

    for claim in draft["claims"]:
        if isinstance(claim, dict) and isinstance(claim.get("text"), str):
            claim["text"] = " ".join(claim["text"].split())
    for item in draft["evidence"]:
        if isinstance(item, dict) and isinstance(item.get("quote"), str):
            item["quote"] = item["quote"].strip()


def _verified_text(draft: dict[str, Any]) -> str:
    if draft["status"] in {"completa", "parcial"}:
        return "\n\n".join(claim["text"] for claim in draft["claims"])
    return _NON_SUBSTANTIVE_TEXT[draft["status"]]


def _plural_limit(count: int, forms: tuple[str, str]) -> str:
    return forms[0 if count == 1 else 1].format(count=count)


def _verified_limits(status: str, outcome: _GraphOutcome) -> list[str]:
    """Publica por qué el resultado no cubre toda la consulta, sin prosa del modelo.

    El borrador nunca aporta este campo: sus `limits` son texto libre y podrían
    colar una conclusión jurídica sin anclaje en una sección que el usuario lee
    como garantía. Lo que sí puede publicarse es lo que el verificador constató
    al recorrer el grafo, porque son hechos con cifras. Un resultado no
    sustantivo no lleva límites: su texto fijo ya dice que no hay respuesta.
    """

    if status not in {"completa", "parcial"}:
        return []
    limits = outcome.limits()
    if status == "parcial" and not limits:
        limits.append(_GENERIC_PARTIAL_LIMIT)
    return limits[:_MAX_LIMITS]


def validate_verbatim_integrity(document: object) -> None:
    """Valida el contrato verbatim y todos sus hashes sin dependencias del proyecto."""

    invalid = ValueError("verbatim integrity validation failed")
    if not isinstance(document, dict) or set(document) != _VERBATIM_KEYS:
        raise invalid
    source_file = document.get("source_file")
    if not isinstance(source_file, str):
        raise invalid
    source_path = PurePosixPath(source_file)
    extractor = document.get("extractor")
    pages = document.get("pages")
    if (
        document.get("schema_version") != "residenciafiscal-verbatim/1"
        or not isinstance(document.get("document_id"), str)
        or not _SAFE_JUDGMENT_ID.fullmatch(document["document_id"])
        or source_path.is_absolute()
        or ".." in source_path.parts
        or "\\" in source_file
        or source_path.suffix.lower() != ".pdf"
        or not isinstance(document.get("source_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", document["source_sha256"])
        or not isinstance(extractor, dict)
        or set(extractor) != {"name", "version"}
        or not all(isinstance(extractor.get(key), str) and extractor[key] for key in extractor)
        or not isinstance(pages, list)
        or not pages
        or not isinstance(document.get("page_count"), int)
        or isinstance(document["page_count"], bool)
        or document["page_count"] != len(pages)
    ):
        raise invalid

    has_extraction_gap = False
    for expected_index, page in enumerate(pages, start=1):
        if not isinstance(page, dict) or set(page) != _VERBATIM_PAGE_KEYS:
            raise invalid
        raw_text = page.get("raw_page_text")
        printed_page = page.get("printed_page")
        extraction_status = page.get("extraction_status")
        if (
            page.get("page_index") != expected_index
            or isinstance(page.get("page_index"), bool)
            or not isinstance(raw_text, str)
            or not (printed_page is None or isinstance(printed_page, str))
            or extraction_status not in {"TEXT_EXTRACTED", "EMPTY_TEXT", "NO_TEXT_RETURNED"}
            or page.get("text_sha256") != hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            or ((raw_text == "") != (extraction_status != "TEXT_EXTRACTED"))
        ):
            raise invalid
        has_extraction_gap = has_extraction_gap or extraction_status != "TEXT_EXTRACTED"

    pages_payload = json.dumps(
        pages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expected_status = "NEEDS_REVIEW" if has_extraction_gap else "COMPLETE"
    if (
        document.get("pages_sha256") != hashlib.sha256(pages_payload).hexdigest()
        or document.get("status") != expected_status
    ):
        raise invalid


def _verify_tool_audit(status: str, audit: list[dict[str, str]] | None) -> None:
    audit = audit or []
    used: set[str] = set()
    for event in audit:
        if (
            not isinstance(event, dict)
            or event.get("type") != "mcp_tool_call"
            or event.get("server") != "corpus"
            or event.get("tool") not in ALLOWED_TOOLS
            or event.get("status") != "completed"
        ):
            raise ValueError("deep research tool audit contains an unexpected call")
        used.add(event["tool"])
    if status in {"completa", "parcial"} and not {"search_corpus", "read_verbatim_page"} <= used:
        raise ValueError("deep research tool audit lacks required corpus reads")


def _parse_draft(draft_text: str) -> dict[str, Any]:
    try:
        draft = json.loads(draft_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Codex draft is not valid JSON") from exc
    if not isinstance(draft, dict) or set(draft) != _DRAFT_KEYS:
        raise ValueError("Codex draft has unexpected fields")
    if (
        draft.get("status") not in _STATUSES
        or not isinstance(draft.get("text"), str)
        or len(draft["text"]) > _MAX_TEXT_CHARS
    ):
        raise ValueError("Codex draft has invalid status or text")
    limits = draft.get("limits")
    claims = draft.get("claims")
    evidence = draft.get("evidence")
    if (
        not isinstance(limits, list)
        or len(limits) > _MAX_LIMITS
        or not all(isinstance(item, str) and len(item) <= _MAX_LIMIT_CHARS for item in limits)
    ):
        raise ValueError("Codex draft has invalid limits")
    if (
        not isinstance(claims, list)
        or len(claims) > _MAX_CLAIMS
        or not isinstance(evidence, list)
        or len(evidence) > _MAX_EVIDENCE
    ):
        raise ValueError("Codex draft has invalid claims or evidence")
    substantive = draft["status"] in {"completa", "parcial"}
    if substantive and (not claims or not evidence):
        raise ValueError("substantive result requires claims and evidence")
    if not substantive and (claims or evidence):
        raise ValueError("non-substantive result cannot contain claims or evidence")
    return draft


def _verify_evidence_graph(draft: dict[str, Any], bundle_path: Path) -> _GraphOutcome:
    evidence = draft["evidence"]
    original_claim_count = len(draft["claims"])
    rollout_sources = _rollout_sources(bundle_path)
    verified_by_original_index: dict[int, dict[str, Any]] = {}
    for original_index, item in enumerate(evidence, start=1):
        try:
            _verify_evidence(item, bundle_path, rollout_sources)
        except UnmatchedEvidenceQuote:
            continue
        assert isinstance(item, dict)
        verified_by_original_index[original_index] = item

    retained_claims: list[tuple[str, list[int]]] = []
    for claim in draft["claims"]:
        text, indexes = _validated_claim(claim, len(evidence))
        claim_evidence = [verified_by_original_index.get(index) for index in indexes]
        if any(item is None for item in claim_evidence):
            continue
        verified_items = [item for item in claim_evidence if item is not None]
        if not _claim_is_grounded(text, verified_items):
            continue
        retained_claims.append((text, indexes))

    used_original_indexes = {index for _text, indexes in retained_claims for index in indexes}
    ordered_original_indexes = sorted(used_original_indexes)
    index_map = {
        original_index: new_index
        for new_index, original_index in enumerate(ordered_original_indexes, start=1)
    }
    verified_evidence = [verified_by_original_index[index] for index in ordered_original_indexes]
    judgments = {item["judgment_id"] for item in verified_evidence}
    if len(judgments) > 5:
        raise ValueError("at most five judgments are allowed")

    draft["claims"] = [
        {
            "text": text,
            "evidence_indexes": [index_map[index] for index in indexes],
        }
        for text, indexes in retained_claims
    ]
    draft["evidence"] = verified_evidence
    graph_changed = (
        len(verified_by_original_index) != len(evidence)
        or len(retained_claims) != original_claim_count
        or len(verified_evidence) != len(evidence)
    )
    if not draft["claims"]:
        draft["status"] = "abstención"
        draft["evidence"] = []
    elif graph_changed:
        draft["status"] = "parcial"
    return _GraphOutcome(
        unmatched_quotes=len(evidence) - len(verified_by_original_index),
        dropped_claims=original_claim_count - len(retained_claims),
    )


def _validated_claim(claim: object, evidence_count: int) -> tuple[str, list[int]]:
    if not isinstance(claim, dict) or set(claim) != {"text", "evidence_indexes"}:
        raise ValueError("deep research claim has invalid fields")
    text = claim.get("text")
    raw_indexes = claim.get("evidence_indexes")
    if isinstance(text, str):
        text = unicodedata.normalize("NFKC", text)
    if (
        not isinstance(text, str)
        or not 20 <= len(text) <= _MAX_CLAIM_CHARS
        or not text.strip()
        or not isinstance(raw_indexes, list)
        or not raw_indexes
        or len(raw_indexes) > 8
        or any(
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 1
            or index > evidence_count
            for index in raw_indexes
        )
    ):
        raise ValueError("deep research claim is invalid")
    indexes = list(dict.fromkeys(raw_indexes))
    return " ".join(text.split()), indexes


def _claim_is_grounded(text: str, evidence: list[dict[str, Any]]) -> bool:
    claim_terms = _grounding_terms(text)
    evidence_terms = {
        term for item in evidence for term in _grounding_terms(str(item.get("quote") or ""))
    }
    if not claim_terms:
        return False
    shared_terms = claim_terms & evidence_terms
    if len(shared_terms) < 2 or len(shared_terms) / len(claim_terms) < _MIN_CLAIM_GROUNDING_RATIO:
        return False
    claim_text = _normalized_phrase_text(text)
    evidence_text = " ".join(
        _normalized_phrase_text(str(item.get("quote") or "")) for item in evidence
    )
    claim_words = set(claim_text.split())
    evidence_words = set(evidence_text.split())
    if claim_words & _NEGATION_TERMS and not evidence_words & _NEGATION_TERMS:
        return False
    return all(
        term not in claim_text or term in evidence_text for term in _REQUIRED_LITERAL_LEGAL_TERMS
    )


def _normalized_phrase_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"\w+", without_accents))


def _grounding_terms(value: str) -> set[str]:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return {
        token[:-2]
        if token.endswith("es") and len(token) > 5
        else token[:-1]
        if token.endswith("s") and len(token) > 4
        else token
        for token in re.findall(r"\w+", normalized)
        if len(token) > 2 and token not in _CLAIM_GROUNDING_STOPWORDS
    }


def _rollout_sources(bundle_path: Path) -> dict[str, str]:
    manifest_path = (bundle_path / "metadata/rollout-manifest.json").resolve()
    if not manifest_path.is_relative_to(bundle_path):
        raise ValueError("rollout manifest path escapes bundle")
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("rollout manifest is unavailable") from exc
    documents = manifest.get("documents") if isinstance(manifest, dict) else None
    if not isinstance(documents, list):
        raise ValueError("rollout manifest has no documents")
    sources: dict[str, str] = {}
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("rollout manifest has an invalid document")
        judgment_id = document.get("judgment_id")
        source_sha256 = document.get("source_sha256")
        if (
            not isinstance(judgment_id, str)
            or not _SAFE_JUDGMENT_ID.fullmatch(judgment_id)
            or not isinstance(source_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
            or judgment_id in sources
        ):
            raise ValueError("rollout manifest has invalid source bindings")
        sources[judgment_id] = source_sha256
    return sources


def _verify_evidence(item: object, bundle_path: Path, rollout_sources: dict[str, str]) -> None:
    if not isinstance(item, dict):
        raise ValueError("invalid evidence")
    required = {"judgment_id", "page", "source_sha256", "quote", "verification"}
    if set(item) != required or item.get("verification") != "EXACT":
        raise ValueError("invalid evidence fields")
    judgment_id = item.get("judgment_id")
    page = item.get("page")
    quote = item.get("quote")
    if not isinstance(judgment_id, str) or not _SAFE_JUDGMENT_ID.fullmatch(judgment_id):
        raise ValueError("invalid evidence judgment_id")
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise ValueError("invalid evidence page")
    if not isinstance(quote, str) or len(quote) < 20 or len(quote) > _MAX_QUOTE_CHARS:
        raise ValueError("invalid evidence literal")
    if not _COMPLETE_QUOTE_END.search(quote):
        raise UnmatchedEvidenceQuote("evidence quote is not a complete sentence")
    document_path = (bundle_path / "verbatim" / f"{judgment_id}.pages.json").resolve()
    if not document_path.is_relative_to(bundle_path):
        raise ValueError("evidence path escapes bundle")
    try:
        document = json.loads(document_path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("evidence document is unavailable") from exc
    validate_verbatim_integrity(document)
    if document.get("document_id") != judgment_id:
        raise ValueError("verbatim document_id does not match evidence judgment")
    canonical_sha256 = rollout_sources.get(judgment_id)
    if canonical_sha256 is None:
        raise ValueError("evidence judgment is absent from rollout manifest")
    if (
        str(item.get("source_sha256", "")).lower() != canonical_sha256
        or str(document.get("source_sha256", "")).lower() != canonical_sha256
    ):
        raise ValueError("evidence source hash does not match rollout manifest")
    pages = document.get("pages")
    source_page = next(
        (
            candidate
            for candidate in pages or []
            if isinstance(candidate, dict) and candidate.get("page_index") == page
        ),
        None,
    )
    if source_page is None:
        raise ValueError("evidence página does not exist")
    raw_text = source_page.get("raw_page_text")
    exact_quote = (
        _unique_raw_whitespace_match(raw_text, quote) if isinstance(raw_text, str) else None
    )
    if exact_quote is None and isinstance(raw_text, str):
        exact_quote = _unique_raw_token_match(raw_text, quote)
    if exact_quote is None or len(exact_quote) > _MAX_QUOTE_CHARS:
        raise UnmatchedEvidenceQuote(
            "evidence página/literal is not an exact raw_page_text substring"
        )
    item["quote"] = exact_quote


def _unique_raw_whitespace_match(raw_text: str, quote: str) -> str | None:
    """Return corpus text only when a whitespace-only variant has one source span."""

    if quote in raw_text:
        return quote
    tokens = re.split(r"\s+", quote)
    if len(tokens) < 2 or any(not token for token in tokens):
        return None
    pattern = r"\s+".join(re.escape(token) for token in tokens)
    matches = list(re.finditer(pattern, raw_text))
    if len(matches) != 1:
        return None
    return matches[0].group(0)


def _unique_raw_token_match(raw_text: str, quote: str) -> str | None:
    """Locate one identical word sequence and return only its raw source span."""

    quote_tokens = [match.group(0).casefold() for match in re.finditer(r"\w+", quote)]
    raw_tokens = list(re.finditer(r"\w+", raw_text))
    if not quote_tokens or len(quote_tokens) > len(raw_tokens):
        return None
    starts = [
        index
        for index in range(len(raw_tokens) - len(quote_tokens) + 1)
        if [token.group(0).casefold() for token in raw_tokens[index : index + len(quote_tokens)]]
        == quote_tokens
    ]
    if len(starts) != 1:
        return None
    start = raw_tokens[starts[0]].start()
    end = raw_tokens[starts[0] + len(quote_tokens) - 1].end()
    while end < len(raw_text) and not raw_text[end].isalnum() and not raw_text[end].isspace():
        end += 1
    return raw_text[start:end]


def estimated_cost_microusd(usage: dict[str, int] | None, pricing: ModelPricing) -> int | None:
    """Calcula el coste con las tarifas versionadas incluidas en el bundle."""

    if not isinstance(usage, dict):
        return None
    counters: list[int] = []
    for key in ("input_tokens", "cache_read_input_tokens", "output_tokens"):
        value = usage.get(key, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return None
        counters.append(value)
    input_tokens, cached_tokens, output_tokens = counters
    if not any(counters):
        return None
    raw_microusd = (
        Decimal(input_tokens + cached_tokens) * pricing.input_microusd_per_token
        + Decimal(output_tokens) * pricing.output_microusd_per_token
    )
    return max(1, int(raw_microusd.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
