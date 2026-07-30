"""Gate final que impide publicar texto no copiado literalmente del PDF."""

from __future__ import annotations

from collections.abc import Sequence

from citation_models import CitationVerification, ExtractedPage


def validate_publishable_fragments(
    verifications: Sequence[CitationVerification],
    pages: Sequence[str | ExtractedPage],
) -> None:
    """Comprueba cada extracto contra la página bruta que declara su match."""

    for verification in verifications:
        if not verification.publishable_literal:
            continue
        for match in verification.fragment_matches:
            page_index = match.pdf_page_index
            excerpt = match.source_excerpt_verbatim
            if page_index is None or excerpt is None or page_index > len(pages):
                raise ValueError("Una cita publicable carece de anclaje válido al PDF")
            page = pages[page_index - 1]
            page_text = page.text if isinstance(page, ExtractedPage) else page
            if excerpt not in page_text:
                raise ValueError(
                    f"El extracto de la página {page_index} no pertenece literalmente al PDF"
                )
