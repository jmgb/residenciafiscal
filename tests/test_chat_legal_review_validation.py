from __future__ import annotations

import json
from pathlib import Path


def _response(label: str) -> str:
    return f"""### Respuesta {label}

- G1 — identificadores y páginas válidos: [x] pasa [ ] falla [ ] N/A
- G2 — afirmaciones sustantivas respaldadas: [x] pasa [ ] falla [ ] N/A
- G3 — distingue hechos, valoración y resultado: [x] pasa [ ] falla [ ] N/A
- G4 — no predice el caso del usuario: [x] pasa [ ] falla [ ] N/A
- G5 — límites transparentes: [x] pasa [ ] falla [ ] N/A

| Dimensión | 0/1/2/N/A | Comentario |
|---|---:|---|
| Fidelidad jurídica | 2 | Correcta |
| Relevancia para la pregunta | 2 | Responde |
| Respaldo de fuentes | 2 | Suficiente |
| Cobertura y contraste | 1 | Cobertura parcial |
| Calibración y límites | 2 | Bien delimitada |
| Claridad y utilidad | 2 | Clara |

**Error crítico:** [x] no [ ] sí

**Observaciones:**

Sin observaciones adicionales.
"""


def _completed_review() -> str:
    return f"""# Formulario de revisión jurídica ciega F0.3

## Declaración inicial del revisor jurídico

- Identificador estable y no personal: REV-F03-01
- Función y cualificación: Abogado especialista en fiscalidad
- Experiencia pertinente en fiscalidad y residencia fiscal: 10 años
- Fecha de inicio: 2026-08-01
- [x] Confirmo que no participé en la generación de las respuestas.
- [x] Confirmo que desconozco la correspondencia X/Y.
- [x] Confirmo que no incluiré datos de clientes ni datos personales.

## Q1

> Pregunta de prueba

{_response("X")}
{_response("Y")}
### Preferencia de la pareja

[x] X  [ ] Y  [ ] empate  [ ] ninguna

**Confianza:** [ ] baja  [x] media  [ ] alta

**Motivo:**

X ofrece mejor cobertura y mantiene los límites.

## Declaración de cierre

- Fecha de cierre: 2026-08-02
- [x] He completado las dieciséis respuestas y las ocho parejas.
- [x] Cada selección contiene una sola opción marcada.
- [x] He motivado los `N/A`, fallos críticos y preferencias.
- [x] No abrí material vedado antes de cerrar la revisión.
- [x] Confirmo que este formulario queda cerrado y listo para versionar.
"""


def test_validador_acepta_formulario_juridico_completo() -> None:
    from chat_legal_review_validation import validate_completed_review

    result = validate_completed_review(_completed_review(), expected_question_ids=("Q1",))

    assert result.valid is True
    assert result.errors == ()


def test_validador_rechaza_seleccion_doble_y_puntuacion_vacia() -> None:
    from chat_legal_review_validation import validate_completed_review

    invalid = _completed_review().replace(
        "[x] pasa [ ] falla [ ] N/A",
        "[x] pasa [x] falla [ ] N/A",
        1,
    )
    invalid = invalid.replace(
        "| Fidelidad jurídica | 2 | Correcta |",
        "| Fidelidad jurídica |  | Correcta |",
        1,
    )

    result = validate_completed_review(invalid, expected_question_ids=("Q1",))

    assert result.valid is False
    assert any("Q1/X/G1" in error for error in result.errors)
    assert any("Q1/X/Fidelidad jurídica" in error for error in result.errors)


def test_validador_rechaza_preguntas_ajenas_al_paquete_congelado() -> None:
    from chat_legal_review_validation import validate_completed_review

    invalid = _completed_review().replace(
        "## Declaración de cierre",
        "## EXTRA-01\n\nPregunta no autorizada.\n\n## Declaración de cierre",
    )

    result = validate_completed_review(invalid, expected_question_ids=("Q1",))

    assert any(error.startswith("preguntas:") for error in result.errors)


def test_cli_valida_ids_del_paquete_y_devuelve_estado(tmp_path: Path) -> None:
    from chat_legal_review_validation import main

    review = tmp_path / "review.md"
    package = tmp_path / "package.json"
    review.write_text(_completed_review(), encoding="utf-8")
    package.write_text(
        json.dumps({"questions": [{"question_id": "Q1"}]}),
        encoding="utf-8",
    )

    assert main(["--review", str(review), "--package-json", str(package)]) == 0

    review.write_text(
        _completed_review().replace("- Fecha de cierre: 2026-08-02", ""), encoding="utf-8"
    )
    assert main(["--review", str(review), "--package-json", str(package)]) == 1
