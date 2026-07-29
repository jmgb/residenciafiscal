"""Pruebas del verificador determinista de citas. No invocan ningún LLM."""

from __future__ import annotations

from dataclasses import replace

import pytest

from citation_source_validation import validate_publishable_fragments
from citation_verification import (
    EvidenceStatus,
    ExtractedPage,
    LiteralFidelity,
    normalize_legal_text,
    parse_page_number,
    split_citation_fragments,
    verify_citation_pages,
)


def test_normaliza_ligaduras_acentos_espacios_y_guiones_de_fin_de_linea() -> None:
    raw = "  No es suﬁ-\n ciente\xa0la RESIDENCIA en España.  "

    assert normalize_legal_text(raw) == "no es suficiente la residencia en espana"


def test_fragmenta_elipsis_y_descarta_fragmentos_demasiado_cortos() -> None:
    quote = (
        '"movimientos de la tarjeta de crédito... restaurantes y repostaje de gasolina '
        '[…] en Bescanó (Gerona)"'
    )

    assert split_citation_fragments(quote) == (
        "movimientos de la tarjeta de credito",
        "restaurantes y repostaje de gasolina",
        "en bescano gerona",
    )


def test_parsea_paginas_con_prefijo_textual() -> None:
    assert parse_page_number("PÁGINA 11") == 11
    assert parse_page_number(7) == 7
    assert parse_page_number("NO CONSTA") is None


def test_verifica_una_cita_exacta_en_la_pagina_declarada() -> None:
    pages = (
        "Primera página sin contenido relevante.",
        "Se entenderá que el contribuyente tiene su residencia habitual en territorio español.",
    )

    result = verify_citation_pages(
        quote="el contribuyente tiene su residencia habitual en territorio español",
        declared_page=2,
        pages=pages,
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.FOUND_DECLARED_PAGE
    assert result.evidence_found is True
    assert result.literal_fidelity is LiteralFidelity.EXACT
    assert result.score == 100
    assert result.matched_pdf_page_indexes == (2,)
    assert result.fragment_matches[0].exact is True


def test_verifica_una_parafrasis_leve_mediante_matching_difuso() -> None:
    pages = (
        "Correspondía al obligado tributario la carga de desvirtuar "
        "las conclusiones alcanzadas por esta Administración.",
    )

    result = verify_citation_pages(
        quote=(
            "correspondía al obligado tributario desvirtuar las conclusiones "
            "alcanzadas por la Administración"
        ),
        declared_page=1,
        pages=pages,
        threshold=80,
    )

    assert result.evidence_status is EvidenceStatus.FOUND_DECLARED_PAGE
    assert result.literal_fidelity is LiteralFidelity.FUZZY_CANDIDATE
    assert 80 <= result.score < 100
    assert result.fragment_matches[0].exact is False
    assert result.fragment_matches[0].source_excerpt_verbatim is None


def test_conserva_el_extracto_verbatim_del_pdf_sin_reconstruirlo() -> None:
    raw_page = (
        "La residencia ﬁs-\ncal del recurrente en España fue acreditada por la Administración."
    )

    result = verify_citation_pages(
        quote="residencia fiscal del recurrente en España",
        declared_page=1,
        pages=(ExtractedPage(1, "1", raw_page),),
        threshold=90,
    )

    assert result.literal is True
    assert (
        result.fragment_matches[0].source_excerpt_verbatim
        == "residencia ﬁs-\ncal del recurrente en España"
    )


def test_todo_extracto_publicable_es_subcadena_del_pdf_sin_reescritura() -> None:
    pages = (
        ExtractedPage(1, "1", "Portada"),
        ExtractedPage(
            2,
            "2",
            "La residencia ﬁs-\ncal del recurrente en España resulta acreditada.",
        ),
    )

    result = verify_citation_pages(
        quote="residencia fiscal del recurrente en España",
        declared_page="2",
        pages=pages,
        threshold=85,
    )

    assert result.publishable_literal is True
    for fragment, page_index in zip(
        result.source_fragments_verbatim,
        result.matched_pdf_page_indexes,
        strict=True,
    ):
        assert fragment in pages[page_index - 1].text

    corrupted_match = replace(
        result.fragment_matches[0],
        source_excerpt_verbatim="Residencia fiscal reescrita",
    )
    corrupted_result = replace(result, fragment_matches=(corrupted_match,))
    with pytest.raises(ValueError, match="no pertenece literalmente"):
        validate_publishable_fragments((corrupted_result,), pages)


def test_busca_en_paginas_adyacentes_antes_que_en_el_resto_del_documento() -> None:
    pages = (
        "Página uno.",
        "Página declarada sin la cita.",
        "Los suministros de agua y electricidad evidencian una continua ocupación.",
        "La misma frase también aparece mucho después: suministros de agua y electricidad.",
    )

    result = verify_citation_pages(
        quote="suministros de agua y electricidad evidencian una continua ocupación",
        declared_page=2,
        pages=pages,
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.FOUND_ADJACENT_PAGE
    assert result.literal_fidelity is LiteralFidelity.EXACT
    assert result.matched_pdf_page_indexes == (3,)


def test_busca_en_el_documento_completo_despues_de_las_adyacentes() -> None:
    pages = (
        "El centro de intereses no aparece aquí.",
        "Página declarada.",
        "Página adyacente.",
        "El núcleo principal de sus actividades o intereses económicos radica en España.",
    )

    result = verify_citation_pages(
        quote="núcleo principal de sus actividades o intereses económicos",
        declared_page=2,
        pages=pages,
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.FOUND_OTHER_PAGE
    assert result.matched_pdf_page_indexes == (4,)


def test_clasifica_como_parcial_si_solo_aparece_un_fragmento() -> None:
    pages = (
        "Los movimientos de la tarjeta de crédito se realizaron en Gerona.",
        "No contiene el segundo fragmento.",
    )

    result = verify_citation_pages(
        quote=(
            "movimientos de la tarjeta de crédito... "
            "la vivienda permanente estaba situada en Francia"
        ),
        declared_page=1,
        pages=pages,
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.PARTIAL_FRAGMENTS
    assert result.evidence_found is False
    assert result.literal_fidelity is LiteralFidelity.PARTIAL
    assert result.matched_fragment_count == 1
    assert result.total_fragment_count == 2
    assert result.score == min(match.score for match in result.fragment_matches)


def test_distingue_documento_sin_texto_de_cita_no_encontrada() -> None:
    extraction_error = verify_citation_pages(
        quote="una cita suficientemente larga para buscar",
        declared_page=1,
        pages=("", "   "),
        threshold=90,
    )
    not_found = verify_citation_pages(
        quote="una cita suficientemente larga para buscar",
        declared_page=1,
        pages=("Texto extraído correctamente, pero completamente distinto.",),
        threshold=90,
    )

    assert extraction_error.evidence_status is EvidenceStatus.EXTRACTION_DEFECT
    assert extraction_error.literal_fidelity is LiteralFidelity.UNVERIFIED
    assert not_found.evidence_status is EvidenceStatus.NOT_FOUND


def test_marca_pagina_declarada_invalida_pero_busca_en_el_documento() -> None:
    pages = ("La residencia habitual se encontraba en Francia durante todo el ejercicio.",)

    result = verify_citation_pages(
        quote="residencia habitual se encontraba en Francia",
        declared_page="NO CONSTA",
        pages=pages,
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.FOUND_OTHER_PAGE
    assert result.declared_pdf_page_index is None
    assert result.declared_page_valid is False


def test_una_cita_vacia_nunca_se_considera_verificada() -> None:
    result = verify_citation_pages(
        quote="  ",
        declared_page=1,
        pages=("Texto extraído correctamente.",),
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.NOT_FOUND
    assert result.score == 0


def test_distingue_indice_pdf_de_etiqueta_de_pagina_impresa() -> None:
    pages = (
        ExtractedPage(pdf_page_index=1, printed_page_label="i", text="Portada."),
        ExtractedPage(pdf_page_index=2, printed_page_label="1", text="Página declarada."),
        ExtractedPage(
            pdf_page_index=3,
            printed_page_label="2",
            text="La vivienda permanente estaba situada en Francia.",
        ),
    )

    result = verify_citation_pages(
        quote="La vivienda permanente estaba situada en Francia.",
        declared_page=2,
        pages=pages,
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.FOUND_ADJACENT_PAGE
    assert result.declared_pdf_page_index == 2
    assert result.matched_pdf_page_indexes == (3,)
    assert result.matched_printed_page_labels == ("2",)
    assert result.fragment_matches[0].pdf_page_index == 3
    assert result.fragment_matches[0].printed_page_label == "2"


def test_elipsis_con_fragmentos_exactos_es_literal() -> None:
    result = verify_citation_pages(
        quote="núcleo principal... intereses económicos",
        declared_page=1,
        pages=("En España radica el núcleo principal de sus actividades e intereses económicos.",),
        threshold=90,
    )

    assert result.evidence_status is EvidenceStatus.FOUND_DECLARED_PAGE
    assert result.literal_fidelity is LiteralFidelity.EXACT_WITH_ELLIPSIS
