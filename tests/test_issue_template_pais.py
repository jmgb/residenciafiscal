"""Contrato de la plantilla de issue para aportar la jurisprudencia de un país.

La invitación es mundial, así que el formulario tiene que entenderse fuera del
mundo hispanohablante: Brasil, Haití o cualquier jurisdicción no hispana llegan
a esta plantilla desde su página de país. Aquí se comprueba mecánicamente que
sigue siendo bilingüe y que no se rompe el prerrellenado que construye
`frontend/src/lib/contribution.ts`.

La convención de la plantilla:

- los `label` llevan los dos idiomas separados por ` / `;
- las `description` largas ponen el español primero y el inglés en una línea
  que empieza por `EN — `.

Sin este gate, una edición en español deja la mitad del formulario sin traducir
y nadie se entera hasta que alguien no lo entiende y no abre la issue.
"""

from pathlib import Path

import yaml

PLANTILLA = Path(__file__).resolve().parents[1] / ".github/ISSUE_TEMPLATE/aportar_pais.yml"

MARCA_EN = "EN — "
SEPARADOR = " / "

#: `contribution.ts` construye `?template=aportar_pais.yml&title=…&pais=<País>`.
#: GitHub solo prerrellena un campo cuyo `id` coincide con el parámetro.
CAMPO_PRERRELLENADO = "pais"


def cargar() -> dict:
    return yaml.safe_load(PLANTILLA.read_text(encoding="utf-8"))


def test_la_plantilla_conserva_el_campo_que_github_prerrellena() -> None:
    plantilla = cargar()
    ids = [bloque.get("id") for bloque in plantilla["body"] if bloque.get("id")]

    assert CAMPO_PRERRELLENADO in ids
    # Renombrar el resto de ids rompería issues abiertas y automatismos.
    assert ids == [
        "pais",
        "fuente",
        "reutilizacion",
        "precepto",
        "volumen",
        "aportacion",
        "revision",
        "contexto",
        "comprobaciones",
    ]


def test_el_nombre_y_la_descripcion_de_la_plantilla_son_bilingues() -> None:
    plantilla = cargar()

    assert SEPARADOR in plantilla["name"]
    assert SEPARADOR in plantilla["description"]


def test_cada_etiqueta_de_campo_esta_en_los_dos_idiomas() -> None:
    plantilla = cargar()

    for bloque in plantilla["body"]:
        etiqueta = bloque.get("attributes", {}).get("label")
        if etiqueta is None:
            continue
        assert SEPARADOR in etiqueta, f"etiqueta sin traducir: {etiqueta!r}"


def test_cada_ayuda_larga_incluye_su_version_en_ingles() -> None:
    plantilla = cargar()

    for bloque in plantilla["body"]:
        atributos = bloque.get("attributes", {})
        texto = atributos.get("description") or atributos.get("value")
        if not texto:
            continue
        assert MARCA_EN in texto, f"texto sin versión inglesa: {texto[:60]!r}"


def test_las_opciones_marcables_tambien_estan_traducidas() -> None:
    """Un desplegable o una casilla sin traducir obliga a elegir a ciegas."""
    plantilla = cargar()

    for bloque in plantilla["body"]:
        for opcion in bloque.get("attributes", {}).get("options", []):
            texto = opcion["label"] if isinstance(opcion, dict) else opcion
            assert SEPARADOR in texto, f"opción sin traducir: {texto!r}"


def test_las_comprobaciones_previas_siguen_siendo_obligatorias() -> None:
    """Traducir no puede aflojar el requisito de no adjuntar documentos."""
    plantilla = cargar()
    (comprobaciones,) = [b for b in plantilla["body"] if b.get("id") == "comprobaciones"]

    opciones = comprobaciones["attributes"]["options"]
    assert len(opciones) == 3
    assert all(opcion["required"] for opcion in opciones)
