"""Verificación reproducible de los artefactos publicados del rollout."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _verificar():
    from jurisprudence_rollout_release import verify_rollout_release

    return verify_rollout_release(
        manifest_path=PROJECT_ROOT / "sentencias/jurisprudence_v3_rollout_106.json",
        output_root=PROJECT_ROOT / "knowledge/jurisprudencia-v3",
        project_root=PROJECT_ROOT,
    )


def test_verifica_manifiesto_corpus_build_y_presupuesto_de_artefactos() -> None:
    result = _verificar()

    assert result.document_count == 106
    assert result.retrieval_document_count == 67
    assert result.retrieval_unit_count == 74
    assert result.publication_status == "AGENT_REVIEWED_ONLY"
    assert result.artifact_bytes < 50_000_000


def test_el_presupuesto_se_mide_por_documento_y_no_solo_en_total() -> None:
    """Un total absoluto no dice nada: el crecimiento es por sentencia.

    Cada documento del rollout deja hoy nueve artefactos —caso, verbatim,
    perfil, índice de recuperación, evaluación, sidecar de roles, proyección
    pública y dos informes—. Con esa forma, el recuento total solo mide cuántas
    sentencias hay; lo que de verdad hay que vigilar es cuántos derivados carga
    cada una, porque es lo que se multiplica al añadir un corpus nuevo.
    """
    from jurisprudence_rollout_release import (
        MAX_ARTIFACT_FILES_PER_DOCUMENT,
        artifact_files_per_document,
    )

    result = _verificar()

    por_documento = artifact_files_per_document(result)
    assert por_documento == pytest.approx(result.artifact_file_count / 106)
    assert por_documento < MAX_ARTIFACT_FILES_PER_DOCUMENT


def test_el_limite_total_deja_sitio_a_una_segunda_jurisdiccion() -> None:
    """La fase E duplica el árbol; el gate no debe saltar por existir."""
    from jurisprudence_rollout_release import MAX_ARTIFACT_FILES

    result = _verificar()

    assert result.artifact_file_count < MAX_ARTIFACT_FILES
    assert MAX_ARTIFACT_FILES >= result.artifact_file_count * 2


def test_el_presupuesto_excedido_dice_cuál_de_los_tres_limites_falla(tmp_path: Path) -> None:
    """Un mensaje genérico obligaba a ir a leer el código para saber qué mover."""
    from jurisprudence_rollout_release import comprobar_presupuesto

    for indice in range(12):
        (tmp_path / f"derivado-{indice}.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="por documento"):
        comprobar_presupuesto(tmp_path, document_count=1)

    with pytest.raises(ValueError, match="bytes"):
        comprobar_presupuesto(tmp_path, document_count=1, max_bytes=1)
