"""Extracción de citas anidadas con propietarios e IDs estables."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from okf_models import OkfCitation, OkfEvidence
from okf_stable_ids import stable_id


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, (list, tuple)) else ()


def _citation(
    *,
    owner_id: str,
    kind: str,
    source_field: str,
    raw: object,
    topic: str,
) -> OkfCitation | None:
    citation = _mapping(raw)
    if citation is None:
        return None
    page = citation.get("pagina")
    text = citation.get("texto")
    if not isinstance(page, str) or not isinstance(text, str) or not text.strip():
        return None
    return OkfCitation(
        id=f"cita-{owner_id}",
        owner_id=owner_id,
        kind=kind,
        source_field=source_field,
        tema=topic,
        pagina=page,
        analysis_quote=text.strip(),
    )


def _standalone_owner_id(prefix: str, raw: Mapping[str, object]) -> str:
    label = str(raw.get("subcategoria") or raw.get("tema") or prefix)
    identity = {
        key: raw.get(key)
        for key in ("parte", "categoria", "subcategoria", "detalle", "tema")
        if raw.get(key) is not None
    }
    return stable_id(prefix, label, identity)


def extract_nested_citations(
    raw: Mapping[str, object],
    pruebas_aeat: Sequence[OkfEvidence],
    pruebas_contribuyente: Sequence[OkfEvidence],
) -> tuple[OkfCitation, ...]:
    """Recorre todos los campos con cita sin usar índices como identidad."""

    citations: list[OkfCitation] = []
    burden = _mapping(raw.get("carga_prueba"))
    if burden:
        candidate = _citation(
            owner_id="carga-prueba",
            kind="carga_prueba",
            source_field="carga_prueba.cita",
            raw=burden.get("cita"),
            topic="carga de la prueba",
        )
        if candidate:
            citations.append(candidate)

    evidence_groups = (
        ("Pruebas_AEAT", "prueba_aeat", pruebas_aeat),
        ("Pruebas_contribuyente", "prueba_contribuyente", pruebas_contribuyente),
    )
    for field, kind, normalized_items in evidence_groups:
        for index, raw_item in enumerate(_sequence(raw.get(field))):
            item = _mapping(raw_item)
            if item is None:
                continue
            candidate = _citation(
                owner_id=normalized_items[index].id,
                kind=kind,
                source_field=f"{field}[{index}].cita",
                raw=item.get("cita"),
                topic=normalized_items[index].subcategoria,
            )
            if candidate:
                citations.append(candidate)

    standalone_groups = (("Pruebas_rechazadas_clave", "prueba-rechazada", "prueba_rechazada"),)
    for field, prefix, kind in standalone_groups:
        for index, raw_item in enumerate(_sequence(raw.get(field))):
            item = _mapping(raw_item)
            if item is None:
                continue
            owner_id = _standalone_owner_id(prefix, item)
            candidate = _citation(
                owner_id=owner_id,
                kind=kind,
                source_field=f"{field}[{index}].cita",
                raw=item.get("cita"),
                topic=str(item.get("subcategoria") or kind),
            )
            if candidate:
                citations.append(candidate)

    decisive = _mapping(raw.get("Prueba_o_bala_de_plata"))
    if decisive:
        owner_id = _standalone_owner_id("prueba-decisiva", decisive)
        candidate = _citation(
            owner_id=owner_id,
            kind="prueba_decisiva",
            source_field="Prueba_o_bala_de_plata.cita",
            raw=decisive.get("cita"),
            topic=str(decisive.get("subcategoria") or "prueba decisiva"),
        )
        if candidate:
            citations.append(candidate)

    for index, raw_item in enumerate(_sequence(raw.get("frases_clave"))):
        item = _mapping(raw_item)
        if item is None:
            continue
        topic = str(item.get("tema") or "frase clave")
        owner_id = stable_id(
            "frase-clave",
            topic,
            {"tema": topic, "texto": item.get("texto")},
        )
        candidate = _citation(
            owner_id=owner_id,
            kind="frase_clave",
            source_field=f"frases_clave[{index}]",
            raw=item,
            topic=topic,
        )
        if candidate:
            citations.append(candidate)
    return tuple(citations)
