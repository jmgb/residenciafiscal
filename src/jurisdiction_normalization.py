"""Convierte `judgment.countries` —texto libre— en códigos del catálogo.

El campo lo escribió un agente sin contrato cerrado, y en los 106 casos conviven
`Mónaco` y `Principado de Mónaco`, `España-Colombia`, `JAPÓN`, `Japón (Tokio)` y
`Reino Unido (CDI 1975; referido también CDI 2013)`. Cruzar país y sentencia
sobre ese campo sin normalizar produce enlaces falsos.

**Esto propone candidatos; no decide nada jurídico.** Que un código aparezca en
una sentencia no dice si esa jurisdicción es la que disputa la residencia, el
lugar donde se practicó una prueba o una mención de paso. Ese papel lo asigna
`jurisdiction_roles.py` a partir de campos tipados del caso.

Dos reglas gobiernan el resultado:

1. **Nada se descarta en silencio.** Una grafía que no resuelve lanza
   `GrafiaDesconocida`; ignorarla dejaría el corpus incompleto sin aviso.
2. **La cadena entera se prueba antes de partirla.** «Bosnia y Herzegovina» y
   «Trinidad y Tobago» son un país cada uno: partir primero por la conjunción
   los convertiría en cuatro países inexistentes.
"""

from __future__ import annotations

import re

from jurisdictions import Jurisdiccion, resolver

# Separadores con los que el corpus enumera varios países en un mismo valor.
# El guion está porque hay valores como «España-Colombia»; ningún nombre del
# catálogo lo lleva dentro, así que no puede partir un país por la mitad.
SEPARADORES = re.compile(r"\s*(?:;|,|/|\s+y\s+|\s*[-–]\s*)\s*")

# Lo que va entre paréntesis nunca es la jurisdicción: es la ciudad, el año del
# convenio o una precisión procesal —«(Tokio)», «(desde septiembre 2007)»,
# «(CDI 1975; referido también CDI 2013)»—.
PARENTESIS = re.compile(r"\([^)]*\)")

# Grafías del corpus que el motor general no resuelve y se declaran a mano, con
# el motivo. Se curan una a una a propósito: la alternativa era recortar
# prefijos genéricos, y «Convenio entre Reino de España» solo se distingue de un
# nombre de país leyéndolo.
GRAFIAS_CORPUS: dict[str, tuple[str, ...]] = {
    # El agente escribió el título del convenio en vez de los países.
    "Convenio entre Reino de España y República Argentina (1991)": ("es", "ar"),
}


class GrafiaDesconocida(ValueError):
    """Un valor de `countries` que no resuelve a ninguna jurisdicción."""


def _resolver_trozos(texto: str) -> tuple[Jurisdiccion, ...] | None:
    """Jurisdicciones de un valor ya limpio, o `None` si alguna no resuelve."""
    completa = resolver(texto)
    if completa is not None:
        return (completa,)

    trozos = [t for t in SEPARADORES.split(texto) if t.strip()]
    if len(trozos) < 2:
        return None

    encontradas: list[Jurisdiccion] = []
    for trozo in trozos:
        jurisdiccion = resolver(trozo)
        if jurisdiccion is None:
            return None
        encontradas.append(jurisdiccion)
    return tuple(encontradas)


def normalizar_grafia_de_pais(valor: str, *, usar_grafias_curadas: bool = True) -> tuple[str, ...]:
    """Códigos de jurisdicción de un valor de `countries`, en orden de aparición.

    `usar_grafias_curadas=False` existe para que un test compruebe que cada
    excepción declarada sigue haciendo falta: una tabla de excepciones que el
    motor ya resuelve engaña a quien la lee.
    """
    if usar_grafias_curadas and valor in GRAFIAS_CORPUS:
        return GRAFIAS_CORPUS[valor]

    limpio = PARENTESIS.sub(" ", valor).strip()
    encontradas = _resolver_trozos(limpio) if limpio else None
    if encontradas is None:
        raise GrafiaDesconocida(
            f"«{valor}» no resuelve a ninguna jurisdicción del catálogo. Añade el alias en "
            "src/jurisdiction_catalog.json o la grafía en GRAFIAS_CORPUS, con su motivo."
        )

    codigos: list[str] = []
    for jurisdiccion in encontradas:
        if jurisdiccion.code not in codigos:
            codigos.append(jurisdiccion.code)
    return tuple(codigos)


def normalizar_paises(valores: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Códigos de una lista `judgment.countries` completa, sin repetidos."""
    codigos: list[str] = []
    for valor in valores:
        for code in normalizar_grafia_de_pais(valor):
            if code not in codigos:
                codigos.append(code)
    return tuple(codigos)
