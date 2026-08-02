"""El convenio que publica cada página de país existe y es el de ese país.

`countryRoutes.json` declara a mano qué convenio de doble imposición corresponde
a cada jurisdicción, porque esa elección es jurídica. Lo que sí es mecánico —y
lo que comprueba este módulo— es que el identificador declarado exista en el
corpus normativo, apunte a un artículo de residencia vigente y pertenezca de
verdad a ese país: una `s` de más en un `BOE-A-` publicaría el convenio de otra
jurisdicción con el nombre correcto encima.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from treaty_relations import instrumento_vigente

PROJECT_ROOT = Path(__file__).parents[1]
COUNTRY_ROUTES = PROJECT_ROOT / "frontend" / "src" / "data" / "countryRoutes.json"
PRECEPTOS = PROJECT_ROOT / "knowledge" / "normativa" / "es" / "preceptos"

# Cómo nombra el BOE a cada país en el título oficial del convenio. Se declaran
# aquí, y no se derivan del nombre de la ruta, precisamente para que el test sea
# independiente del dato que verifica: «Suiza» no aparece en el título del
# convenio de 1967, que dice «Confederación Suiza».
NOMBRE_EN_LA_NORMA: dict[str, str] = {
    "/estados-unidos": "Estados Unidos de América",
    "/portugal": "República Portuguesa",
    "/francia": "República Francesa",
    "/reino-unido": "Reino Unido de Gran Bretaña",
    "/alemania": "República Federal de Alemania",
    "/suiza": "Confederación Suiza",
    "/andorra": "Principado de Andorra",
    "/italia": "España e Italia",
    "/mexico": "Estados Unidos Mexicanos",
    "/argentina": "República Argentina",
    "/bolivia": "República de Bolivia",
    "/brasil": "República Federativa del Brasil",
    "/chile": "República de Chile",
    "/colombia": "República de Colombia",
    "/costa-rica": "República de Costa Rica",
    "/cuba": "República de Cuba",
    "/ecuador": "España y Ecuador",
    "/el-salvador": "República de El Salvador",
    "/panama": "República de Panamá",
    "/paraguay": "República del Paraguay",
    "/republica-dominicana": "República Dominicana",
    "/uruguay": "República Oriental del Uruguay",
    "/venezuela": "República Bolivariana de Venezuela",
    "/marruecos": "Reino de Marruecos",
    "/rusia": "Federación Rusa",
    "/emiratos-arabes-unidos": "Emiratos Árabes Unidos",
    "/kuwait": "Estado de Kuwait",
}

# Países sin convenio en vigor con España según la relación oficial de la AEAT.
# Declararlo es una afirmación de la web, así que se fija aquí igual que el
# resto: si algún día se firma uno, este test obliga a revisarlo.
SIN_CONVENIO = ("/monaco", "/guatemala", "/haiti", "/honduras", "/nicaragua", "/peru")


def _rutas() -> list[dict]:
    """Rutas de país con el convenio que les corresponde ya resuelto.

    `treatyBoeId` dejó de estar en el JSON: la relación bilateral es dato de
    dominio y vive en `treaty_relations_es.json`. Este test sigue siendo la
    verificación independiente de que ese identificador es de verdad el
    convenio de ese país, porque lo contrasta con el título oficial del BOE.
    """
    rutas = json.loads(COUNTRY_ROUTES.read_text(encoding="utf-8"))
    for ruta in rutas:
        vigente = instrumento_vigente(ruta["code"])
        ruta["treatyBoeId"] = vigente.boe_id if vigente else None
    return rutas


def _preceptos_por_boe_id() -> dict[str, tuple[dict, str]]:
    """Frontmatter y Markdown completo de cada precepto, indexados por norma."""
    preceptos: dict[str, tuple[dict, str]] = {}
    for fichero in PRECEPTOS.glob("*.md"):
        texto = fichero.read_text(encoding="utf-8")
        if not texto.startswith("---"):
            continue
        frontmatter = yaml.safe_load(texto.split("---", 2)[1])
        preceptos[frontmatter["boe_id"]] = (frontmatter, texto)
    return preceptos


def test_cada_pais_declara_el_convenio_que_le_corresponde() -> None:
    preceptos = _preceptos_por_boe_id()

    for ruta in _rutas():
        boe_id = ruta["treatyBoeId"]
        if boe_id is None:
            continue
        assert boe_id in preceptos, f"{ruta['path']}: {boe_id} no está en el corpus normativo"
        precepto, _ = preceptos[boe_id]
        esperado = NOMBRE_EN_LA_NORMA[ruta["path"]]
        assert esperado in precepto["norma"], (
            f"{ruta['path']}: el convenio {boe_id} no es de ese país, "
            f"su título oficial dice «{precepto['norma'][:80]}…»"
        )
        # Publicar un convenio sustituido como si rigiera hoy sería peor que no
        # publicar nada: el visitante leería derecho que ya no se aplica.
        assert precepto["grupo"] == "cdi", f"{ruta['path']}: {boe_id} no es un convenio vigente"
        assert precepto["derogada"] is False, f"{ruta['path']}: {boe_id} está derogado"
        # Sin enlace oficial la página no podría remitir a la fuente.
        assert precepto["url_boe"], f"{ruta['path']}: {boe_id} no tiene URL del BOE"
        assert precepto["url_boe"].startswith("https://www.boe.es/")


def test_el_articulo_publicado_es_el_de_residencia() -> None:
    preceptos = _preceptos_por_boe_id()

    for ruta in _rutas():
        boe_id = ruta["treatyBoeId"]
        if boe_id is None:
            continue
        _, texto = preceptos[boe_id]
        # La firma sustantiva del artículo de residencia del Modelo OCDE. Es lo
        # que hace útil la página: la regla que decide de qué Estado es
        # residente quien podría serlo de los dos.
        assert "residente de ambos" in texto.lower() or "residente de los dos" in texto.lower(), (
            f"{ruta['path']}: el precepto publicado no resuelve la doble residencia"
        )


def test_un_convenio_bajado_del_diario_no_se_rotula_como_derogado() -> None:
    """Venezuela y Paraguay salen del diario porque el BOE no los consolida.

    Es un dato sobre el origen del fichero, no sobre su vigencia: si el
    generador confundiera ambas cosas, la página publicaría derecho aplicable
    bajo el rótulo «Texto derogado».
    """
    preceptos = _preceptos_por_boe_id()

    for boe_id in ("BOE-A-2004-11070", "BOE-A-2024-15573"):
        frontmatter, texto = preceptos[boe_id]
        assert frontmatter["derogada"] is False
        assert frontmatter["nota_derogacion"] is None
        assert "# Texto vigente" in texto
        assert "# Texto derogado" not in texto
        assert "Norma derogada" not in texto
        # Pero sí dice de dónde viene, porque el consolidado es lo habitual.
        assert "publicación original" in texto.lower()
        assert "texto publicado en el diario" in texto
        # Y el enlace no promete un ancla que la ficha del diario no tiene.
        assert frontmatter["url_boe"] == f"https://www.boe.es/buscar/doc.php?id={boe_id}"


def test_los_paises_sin_convenio_lo_declaran_explicitamente() -> None:
    rutas = {ruta["path"]: ruta for ruta in _rutas()}

    for path in SIN_CONVENIO:
        assert rutas[path]["treatyBoeId"] is None, f"{path} ya tiene convenio declarado"

    # España no tiene convenio consigo misma: su marco es el art. 9 LIRPF, que
    # ya viaja en `legalReferences`.
    assert rutas["/espana"]["treatyBoeId"] is None
    assert rutas["/espana"]["legalReferences"][0]["shortCitation"] == "Art. 9 LIRPF"

    declarados = {ruta["path"] for ruta in _rutas() if ruta["treatyBoeId"] is None}
    assert declarados == {*SIN_CONVENIO, "/espana"}
