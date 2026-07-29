"""Pruebas del verificador determinista de citas. No invocan ningún LLM."""

from __future__ import annotations

from citation_verification import (
    CitationStatus,
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

    assert result.status is CitationStatus.VERIFIED_DECLARED_PAGE
    assert result.score == 100
    assert result.matched_pages == (2,)
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

    assert result.status is CitationStatus.VERIFIED_DECLARED_PAGE
    assert 80 <= result.score < 100
    assert result.fragment_matches[0].exact is False


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

    assert result.status is CitationStatus.VERIFIED_ADJACENT_PAGE
    assert result.matched_pages == (3,)


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

    assert result.status is CitationStatus.VERIFIED_OTHER_PAGE
    assert result.matched_pages == (4,)


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

    assert result.status is CitationStatus.PARTIAL_FRAGMENTS
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

    assert extraction_error.status is CitationStatus.EXTRACTION_DEFECT
    assert not_found.status is CitationStatus.NOT_FOUND


def test_marca_pagina_declarada_invalida_pero_busca_en_el_documento() -> None:
    pages = ("La residencia habitual se encontraba en Francia durante todo el ejercicio.",)

    result = verify_citation_pages(
        quote="residencia habitual se encontraba en Francia",
        declared_page="NO CONSTA",
        pages=pages,
        threshold=90,
    )

    assert result.status is CitationStatus.VERIFIED_OTHER_PAGE
    assert result.declared_page is None
    assert result.declared_page_valid is False


def test_una_cita_vacia_nunca_se_considera_verificada() -> None:
    result = verify_citation_pages(
        quote="  ",
        declared_page=1,
        pages=("Texto extraído correctamente.",),
        threshold=90,
    )

    assert result.status is CitationStatus.NOT_FOUND
    assert result.score == 0
