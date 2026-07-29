"""Tests de la reanudación (`--skip-existing` / `--resume-from`). Sin coste de LLM.

Regresión: `main()` nombra el JSONL con un timestamp nuevo en cada ejecución, y
`main_async` comprobaba `skip_existing and jsonl_path.exists()` sobre ese fichero
recién nombrado — que nunca existe. Resultado: `--skip-existing` no saltaba nada y
reprocesaba los 106 PDFs. `find_latest_jsonl()` resuelve el JSONL previo real.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from residenciafiscal import find_latest_jsonl


def test_devuelve_none_si_no_hay_ejecuciones_previas(tmp_path: Path) -> None:
    assert find_latest_jsonl(tmp_path, "analisis.jsonl") is None


def test_devuelve_none_si_el_directorio_no_existe(tmp_path: Path) -> None:
    assert find_latest_jsonl(tmp_path / "no-existe", "analisis.jsonl") is None


def test_elige_el_jsonl_mas_reciente_por_mtime(tmp_path: Path) -> None:
    antiguo = tmp_path / "analisis_01012026_120000.jsonl"
    reciente = tmp_path / "analisis_02012026_090000.jsonl"
    antiguo.write_text('{"archivo": "a.pdf"}\n', encoding="utf-8")
    reciente.write_text('{"archivo": "b.pdf"}\n', encoding="utf-8")

    # mtime explícito: no dependemos del orden de creación ni del reloj.
    os.utime(antiguo, (1_000_000, 1_000_000))
    os.utime(reciente, (2_000_000, 2_000_000))

    assert find_latest_jsonl(tmp_path, "analisis.jsonl") == reciente


def test_ignora_ficheros_de_otro_prefijo(tmp_path: Path) -> None:
    (tmp_path / "analisis_01012026_120000.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "otracosa_09092026_120000.jsonl").write_text("{}\n", encoding="utf-8")

    encontrado = find_latest_jsonl(tmp_path, "analisis.jsonl")
    assert encontrado is not None
    assert encontrado.name.startswith("analisis_")


def test_el_jsonl_hallado_permite_reconstruir_los_ya_procesados(tmp_path: Path) -> None:
    """Comprueba el contrato que consume main_async: una línea JSON por sentencia."""
    previo = tmp_path / "analisis_01012026_120000.jsonl"
    previo.write_text(
        '{"archivo": "STS_1.pdf"}\n'
        "\n"  # línea en blanco: main_async la ignora
        '{"archivo": "STS_2.pdf"}\n',
        encoding="utf-8",
    )

    hallado = find_latest_jsonl(tmp_path, "analisis.jsonl")
    assert hallado is not None

    procesados = {
        json.loads(linea)["archivo"]
        for linea in hallado.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    }
    assert procesados == {"STS_1.pdf", "STS_2.pdf"}
