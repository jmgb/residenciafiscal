"""Resuelve las citas normativas de las sentencias al precepto publicado.

Los análisis del corpus citan la norma en texto libre —«art.9 LIRPF»,
«artículo 105.1 LGT», «art. 4.2 CDI»— y hasta ahora nada conectaba esa cita con
`knowledge/normativa/es/preceptos/lirpf-a9.md`. Este módulo hace ese enlace, sin
LLM y sin tocar ninguno de los dos corpus: produce un artefacto aparte.

Tres reglas gobiernan el resultado, y las tres existen para no inventar derecho:

1. **Solo se enlaza a preceptos publicados.** Si una sentencia cita el art. 13
   TRLIRNR, que no está en la selección, la cita se registra como no resuelta.
   Nunca se apunta a un fichero que no existe ni se deduce contenido.
2. **La certeza se declara.** «art.9 LIRPF» trae la norma explícita; «art. 9.1.a»
   no. La segunda se resuelve por la norma de residencia aplicable a los
   ejercicios de esa sentencia, y queda marcada como `inferida` para que el chat
   pueda preferir las explícitas y una persona pueda auditarlas.
3. **La redacción se elige por ejercicio.** Un precepto puede haber cambiado
   entre el ejercicio enjuiciado y hoy; el enlace dice qué redacción regía
   entonces, que es la única que la sentencia pudo aplicar.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# --- Normas del corpus -------------------------------------------------------

# Siglas tal como las escriben los análisis, con la norma a la que apuntan.
NORMA_POR_SIGLA: dict[str, str] = {
    "lirpf": "BOE-A-2006-20764",
    "lgt": "BOE-A-2003-23186",
    "trlirnr": "BOE-A-2004-4527",
    "lirnr": "BOE-A-2004-4527",
    "irnr": "BOE-A-2004-4527",
    "rirpf": "BOE-A-2007-6820",
    "trlirpf": "BOE-A-2004-4347",
}

# La Ley 35/2006 rige desde el ejercicio 2007; antes regía el texto refundido de
# 2004. Determina a qué norma apunta una cita sin sigla y permite detectar
# anacronismos —una sentencia de 2005 que cite «LIRPF»—.
PRIMER_EJERCICIO_LIRPF = 2007
NORMA_RESIDENCIA_HASTA_2006 = "BOE-A-2004-4347"
NORMA_RESIDENCIA_DESDE_2007 = "BOE-A-2006-20764"

# Siglas que denotan el convenio aplicable al caso, no una norma fija: se
# resuelven con el país del CDI que declara la propia sentencia.
SIGLAS_CONVENIO = frozenset({"cdi", "convenio"})


@dataclass(frozen=True)
class ConvenioPais:
    """Convenio de un país, con los ejercicios que rige.

    Los rangos son necesarios porque dos países del corpus tienen convenio
    antiguo y moderno, y una sentencia sobre un ejercicio viejo aplica el viejo.
    """

    boe_id: str
    desde_ejercicio: int | None = None
    hasta_ejercicio: int | None = None

    def rige(self, ejercicio: int | None) -> bool:
        if ejercicio is None:
            return self.desde_ejercicio is None and self.hasta_ejercicio is None
        if self.desde_ejercicio is not None and ejercicio < self.desde_ejercicio:
            return False
        return not (self.hasta_ejercicio is not None and ejercicio > self.hasta_ejercicio)


# Convenios de los países que aparecen en el corpus. Es una tabla curada y
# corta a propósito: deducir el país del título del convenio es inseguro —los 96
# lo escriben de trece formas— y un país equivocado aquí enlazaría una sentencia
# con el derecho de otro Estado.
CONVENIOS_POR_PAIS: dict[str, tuple[ConvenioPais, ...]] = {
    "reino unido": (
        ConvenioPais("BOE-A-1976-23347", hasta_ejercicio=2013),
        ConvenioPais("BOE-A-2014-5171", desde_ejercicio=2014),
    ),
    "argentina": (
        ConvenioPais("BOE-A-1994-20084", hasta_ejercicio=2012),
        ConvenioPais("BOE-A-2014-373", desde_ejercicio=2013),
    ),
    "suiza": (ConvenioPais("BOE-A-1967-3470"),),
    "francia": (ConvenioPais("BOE-A-1997-12729"),),
    "alemania": (ConvenioPais("BOE-A-2012-10212"),),
    "paises bajos": (ConvenioPais("BOE-A-1972-1469"),),
    "holanda": (ConvenioPais("BOE-A-1972-1469"),),
    "colombia": (ConvenioPais("BOE-A-2008-17209"),),
    "emiratos arabes unidos": (ConvenioPais("BOE-A-2007-1343"),),
    "rusia": (ConvenioPais("BOE-A-2000-12779"),),
    "federacion rusa": (ConvenioPais("BOE-A-2000-12779"),),
    "japon": (ConvenioPais("BOE-A-1974-1930", hasta_ejercicio=2020),),
    "marruecos": (ConvenioPais("BOE-A-1985-9280"),),
    "estados unidos": (ConvenioPais("BOE-A-1990-30940"),),
    "eeuu": (ConvenioPais("BOE-A-1990-30940"),),
    "mexico": (ConvenioPais("BOE-A-1994-23743"),),
    "mejico": (ConvenioPais("BOE-A-1994-23743"),),
    "canada": (ConvenioPais("BOE-A-1981-2731"),),
}

# Valores del campo `pais_CDI_aplicado` que no nombran ningún país.
SIN_PAIS = frozenset({"", "no consta", "no aplica", "ninguno", "n/a", "null", "no"})

# --- Extracción de citas -----------------------------------------------------

# «art.9 LIRPF», «artículo 105.1 LGT», «art. 9.1.a», «arts. 8.1.a», «art. 4.2 CDI».
# El apartado se captura pero no participa en la resolución: el fichero publicado
# es el artículo completo, y recortarlo sería reconstruir texto legal.
PATRON_CITA = re.compile(
    r"\b(?:art[íi]culos?|arts?)\.?\s*"
    r"(?P<numero>\d{1,3})(?:\s*(?P<sufijo>bis|ter))?"
    r"(?P<apartado>(?:\.\d+)*(?:\.[a-z]\)?)?)"
    r"(?:\s*(?:de\s+la|de\s+los|del|de)?\s*"
    r"(?P<norma>LIRPF|LGT|TRLIRNR|LIRNR|IRNR|RIRPF|TRLIRPF|CDI|Convenio))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CitaBruta:
    """Una cita tal como aparece en el texto, antes de resolverse."""

    texto: str
    numero: str
    sufijo: str | None
    apartado: str
    sigla: str | None
    campo: str


@dataclass(frozen=True)
class EnlaceCita:
    """Una cita ya resuelta a un precepto publicado."""

    texto_citado: str
    campo: str
    slug: str
    boe_id: str
    bloque_id: str
    apartado: str | None
    certeza: str
    redaccion_aplicable: dict[str, str | None] = field(default_factory=dict)


def sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


# «Artículo 9», «Artículo 95 bis», «Artículo IV»: el número con el que una cita
# puede referirse al precepto. No se construye el identificador de bloque a
# partir del número porque el BOE no lo hace uniforme: la LIRPF usa `a9`, pero
# entre los convenios aparecen `a4`, `ar-4`, `ai-4` y `a1-5` para el artículo 4.
#
# La alternativa romana no es teórica: los convenios con Suecia, Rumanía y Canadá
# titulan su artículo de residencia «Artículo IV», mientras las sentencias lo
# citan en árabe. El `(?!\w)` final evita que un ordinal escrito con letra
# —«Artículo Duodécimo» empieza por `D`— se lea como numeración romana.
NUMERO_DESIGNACION = re.compile(
    r"^Art[íi]culo\s*(?P<numero>\d+|[IVXLCDM]+)(?:\s*(?P<sufijo>bis|ter))?(?!\w)",
    re.I,
)

# Romano bien formado y canónico: descarta `IIII` o `VX`, que convertidos darían
# un número inventado y mandarían a un artículo distinto del citado.
ROMANO_CANONICO = re.compile(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")

VALOR_ROMANO = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _a_arabigo(numero: str) -> str | None:
    """Normaliza a árabe el número de una designación. `None` si no es válido."""
    if numero.isdigit():
        return numero
    romano = numero.upper()
    if not ROMANO_CANONICO.fullmatch(romano):
        return None
    total = 0
    mayor = 0
    # De derecha a izquierda: un símbolo menor que el ya visto resta (IV = 4).
    for simbolo in reversed(romano):
        valor = VALOR_ROMANO[simbolo]
        total += valor if valor >= mayor else -valor
        mayor = max(mayor, valor)
    return str(total)


def numero_de_designacion(designacion: str) -> str | None:
    """«Artículo 95 bis» -> `95bis`; «Artículo IV» -> `4`.

    `None` si la designación no es un artículo numerado (una disposición
    transitoria, un ordinal escrito con letra o un romano mal formado).
    """
    coincidencia = NUMERO_DESIGNACION.match(designacion)
    if not coincidencia:
        return None
    numero = _a_arabigo(coincidencia.group("numero"))
    if numero is None:
        return None
    return numero + (coincidencia.group("sufijo") or "").lower()


def numero_citado(cita: CitaBruta) -> str:
    return cita.numero + (cita.sufijo or "").lower()


def extraer_citas(texto: str, campo: str) -> list[CitaBruta]:
    citas: list[CitaBruta] = []
    for coincidencia in PATRON_CITA.finditer(texto):
        sigla = coincidencia.group("norma")
        citas.append(
            CitaBruta(
                texto=coincidencia.group(0).strip(),
                numero=coincidencia.group("numero"),
                sufijo=coincidencia.group("sufijo"),
                apartado=coincidencia.group("apartado") or "",
                sigla=sigla.lower() if sigla else None,
                campo=campo,
            )
        )
    return citas


def recorrer_textos(valor: object, prefijo: str = "") -> list[tuple[str, str]]:
    """Devuelve todas las cadenas de un registro con la ruta del campo.

    Las citas normativas están repartidas por el registro —`resumen_criterios`,
    `carga_prueba.motivo`, el detalle de cada prueba— y limitarse a unos campos
    dejaría fuera la mitad.
    """
    if isinstance(valor, str):
        return [(prefijo, valor)] if valor else []
    if isinstance(valor, dict):
        return [
            par
            for clave, sub in valor.items()
            for par in recorrer_textos(sub, f"{prefijo}.{clave}" if prefijo else str(clave))
        ]
    if isinstance(valor, list):
        return [
            par
            for indice, sub in enumerate(valor)
            for par in recorrer_textos(sub, f"{prefijo}[{indice}]")
        ]
    return []


def extraer_ejercicios(valor: object) -> list[int]:
    """Los ejercicios llegan como texto libre: «2010 y 2011», «2010-2012»."""
    if valor is None:
        return []
    texto = valor if isinstance(valor, str) else str(valor)
    return sorted({int(a) for a in re.findall(r"\b(19\d{2}|20\d{2})\b", texto)})


def paises_citados(valor: object) -> list[str]:
    """Países reconocidos en un campo como `pais_CDI_aplicado`.

    El campo es texto libre del modelo: «Méjico», «EEUU», «Marruecos; Estados
    Unidos», «Reino Unido (CDI 1975; referido también CDI 2013)». Se buscan los
    alias conocidos como subcadena, sin acentos, y se admite más de uno.
    """
    if valor is None:
        return []
    normalizado = sin_acentos(str(valor))
    if normalizado.strip() in SIN_PAIS:
        return []
    encontrados = [alias for alias in CONVENIOS_POR_PAIS if alias in normalizado]
    # «paises bajos» y «holanda» apuntan al mismo convenio; se deduplica por id.
    vistos: set[str] = set()
    unicos: list[str] = []
    for alias in sorted(encontrados, key=len, reverse=True):
        ids = {c.boe_id for c in CONVENIOS_POR_PAIS[alias]}
        if ids & vistos:
            continue
        vistos |= ids
        unicos.append(alias)
    return unicos


def normas_residencia_aplicables(ejercicios: list[int]) -> list[str]:
    """Normas internas de residencia que rigen los ejercicios de una sentencia.

    Devuelve una lista y no una norma porque un caso puede abarcar ejercicios a
    ambos lados de la entrada en vigor de la Ley 35/2006, y entonces cada periodo
    se rige por la suya. Elegir una sola por el ejercicio más alto dejaba los
    anteriores sin la norma que de verdad los regía.
    """
    if not ejercicios:
        return [NORMA_RESIDENCIA_DESDE_2007]
    normas = []
    if any(ejercicio < PRIMER_EJERCICIO_LIRPF for ejercicio in ejercicios):
        normas.append(NORMA_RESIDENCIA_HASTA_2006)
    if any(ejercicio >= PRIMER_EJERCICIO_LIRPF for ejercicio in ejercicios):
        normas.append(NORMA_RESIDENCIA_DESDE_2007)
    return normas


def ejercicios_regidos_por(boe_id: str, ejercicios: list[int]) -> list[int]:
    """Ejercicios del caso que rige esa norma interna de residencia.

    Acota la redacción aplicable a su periodo: sin esto, el texto refundido de
    2004 aparecía con una redacción para un ejercicio en el que ya estaba
    derogado.
    """
    if boe_id == NORMA_RESIDENCIA_HASTA_2006:
        return [e for e in ejercicios if e < PRIMER_EJERCICIO_LIRPF]
    if boe_id == NORMA_RESIDENCIA_DESDE_2007:
        return [e for e in ejercicios if e >= PRIMER_EJERCICIO_LIRPF]
    return ejercicios


# --- Preceptos publicados ----------------------------------------------------


@dataclass(frozen=True)
class PreceptoPublicado:
    """Lo que el corpus normativo ofrece como destino de un enlace."""

    slug: str
    jurisdiccion: str
    boe_id: str
    bloque_id: str
    designacion: str
    titulo: str
    derogada: bool
    versiones: tuple[str | None, ...]

    @property
    def numero(self) -> str | None:
        return numero_de_designacion(self.designacion)

    def redaccion_para(self, ejercicio: int) -> str | None:
        """Fecha de vigencia de la redacción que regía el ejercicio dado.

        Un ejercicio se cierra el 31 de diciembre, así que rige la última
        redacción que hubiera entrado en vigor dentro de ese año o antes.
        """
        limite = f"{ejercicio}-12-31"
        aplicables = [v for v in self.versiones if v and v <= limite]
        return max(aplicables) if aplicables else None


def cargar_preceptos(directorio: Path) -> dict[str, list[PreceptoPublicado]]:
    """Indexa por norma los preceptos publicados.

    El resolvedor solo puede enlazar a lo que existe, así que el catálogo se lee
    del corpus generado y no de una lista paralela que podría desincronizarse.
    """
    catalogo: dict[str, list[PreceptoPublicado]] = defaultdict(list)
    for fichero in sorted(directorio.glob("*.md")):
        if fichero.name == "index.md":
            continue
        frontmatter = yaml.safe_load(fichero.read_text(encoding="utf-8").split("---", 2)[1])
        catalogo[str(frontmatter["boe_id"])].append(
            PreceptoPublicado(
                slug=fichero.stem,
                jurisdiccion=str(frontmatter["jurisdiccion"]),
                boe_id=str(frontmatter["boe_id"]),
                bloque_id=str(frontmatter["bloque_id"]),
                designacion=str(frontmatter["designacion"]),
                titulo=str(frontmatter["title"]),
                derogada=bool(frontmatter["derogada"]),
                versiones=tuple(v.get("fecha_vigencia") for v in frontmatter["versiones"]),
            )
        )
    return dict(catalogo)


def buscar_precepto(
    catalogo: dict[str, list[PreceptoPublicado]], boe_id: str, numero: str
) -> PreceptoPublicado | None:
    """Precepto publicado de esa norma cuyo artículo es el citado."""
    for precepto in catalogo.get(boe_id, ()):
        if precepto.numero == numero:
            return precepto
    return None


# --- Resolución --------------------------------------------------------------

CERTEZA_EXPLICITA = "explicita"
CERTEZA_INFERIDA = "inferida"


def _redacciones_por_ejercicio(
    precepto: PreceptoPublicado, ejercicios: list[int]
) -> dict[str, str | None]:
    return {str(ejercicio): precepto.redaccion_para(ejercicio) for ejercicio in ejercicios}


def _vigentes(convenios: list[ConvenioPais], ejercicios: list[int]) -> list[ConvenioPais]:
    """Convenios del país que rigieron **alguno** de los ejercicios del caso.

    Un país puede haber cambiado de convenio en medio del periodo enjuiciado —el
    de Reino Unido rige hasta 2013 y el nuevo desde 2014—, así que filtrar por el
    ejercicio más alto descartaba el convenio que regía los primeros años.
    """
    if not ejercicios:
        return [c for c in convenios if c.rige(None)]
    return [c for c in convenios if any(c.rige(ejercicio) for ejercicio in ejercicios)]


def _ejercicios_del_enlace(
    boe_id: str, convenios: list[ConvenioPais], ejercicios: list[int]
) -> list[int]:
    """Ejercicios del caso a los que se aplica realmente la norma enlazada."""
    del_convenio = [c for c in convenios if c.boe_id == boe_id]
    if del_convenio:
        return [e for e in ejercicios if any(c.rige(e) for c in del_convenio)]
    return ejercicios_regidos_por(boe_id, ejercicios)


MOTIVO_SIN_PAIS_CDI = "La sentencia no declara de qué país es el convenio que cita"
MOTIVO_SIGLA_DESCONOCIDA = "La sigla de la norma no está en el corpus normativo"
MOTIVO_ARTICULO_NO_PUBLICADO = (
    "De los convenios solo se publica su artículo de residencia, y la cita apunta a otro"
)
MOTIVO_PRECEPTO_NO_PUBLICADO = "El artículo citado no está entre los preceptos publicados"


def resolver_cita(
    cita: CitaBruta,
    catalogo: dict[str, list[PreceptoPublicado]],
    ejercicios: list[int],
    convenios: list[ConvenioPais],
) -> tuple[list[EnlaceCita], str | None]:
    """Enlaces de una cita y, si no hay ninguno, el motivo concreto.

    El motivo importa: «no se ha podido resolver» sirve de poco, mientras que
    distinguir entre «la sentencia no dice de qué país es el convenio» y «ese
    artículo del convenio no se publica» dice exactamente qué haría falta para
    resolverla.
    """
    numero = numero_citado(cita)
    es_convenio = cita.sigla in SIGLAS_CONVENIO

    if es_convenio:
        # «art. 4.2 CDI» no dice de qué país: lo dice la propia sentencia.
        objetivos = [(c.boe_id, CERTEZA_EXPLICITA) for c in _vigentes(convenios, ejercicios)]
        if not objetivos:
            return [], MOTIVO_SIN_PAIS_CDI
    elif cita.sigla:
        boe_id = NORMA_POR_SIGLA.get(cita.sigla)
        if boe_id is None:
            return [], MOTIVO_SIGLA_DESCONOCIDA
        objetivos = [(boe_id, CERTEZA_EXPLICITA)]
    else:
        # Sin sigla, la cita puede ser de la norma interna de residencia —el
        # objeto de todo el corpus— o del convenio que la sentencia invoca.
        # Ambas quedan marcadas como inferidas; el filtro de «solo preceptos
        # publicados» es lo que evita enlazar cualquier cosa.
        objetivos = [
            (boe_id, CERTEZA_INFERIDA) for boe_id in normas_residencia_aplicables(ejercicios)
        ]
        objetivos += [(c.boe_id, CERTEZA_INFERIDA) for c in _vigentes(convenios, ejercicios)]

    enlaces: list[EnlaceCita] = []
    for boe_id, certeza in objetivos:
        precepto = buscar_precepto(catalogo, boe_id, numero)
        if precepto is None:
            continue
        enlaces.append(
            EnlaceCita(
                texto_citado=cita.texto,
                campo=cita.campo,
                slug=precepto.slug,
                boe_id=precepto.boe_id,
                bloque_id=precepto.bloque_id,
                apartado=cita.apartado.lstrip(".") or None,
                certeza=certeza,
                redaccion_aplicable=_redacciones_por_ejercicio(
                    precepto, _ejercicios_del_enlace(boe_id, convenios, ejercicios)
                ),
            )
        )
    if enlaces:
        return enlaces, None
    return [], MOTIVO_ARTICULO_NO_PUBLICADO if es_convenio else MOTIVO_PRECEPTO_NO_PUBLICADO


def _clave_enlace(enlace: EnlaceCita) -> tuple[str, str, str | None, str]:
    return (enlace.slug, enlace.texto_citado.lower(), enlace.apartado, enlace.certeza)


def enlazar_registro(
    registro: dict,
    catalogo: dict[str, list[PreceptoPublicado]],
) -> dict:
    """Resuelve todas las citas normativas de un registro del JSONL."""
    ejercicios = extraer_ejercicios(registro.get("ejercicios_afectados"))
    convenios = [
        convenio
        for alias in paises_citados(registro.get("pais_CDI_aplicado"))
        for convenio in CONVENIOS_POR_PAIS[alias]
    ]

    enlaces: dict[tuple[str, str, str | None, str], EnlaceCita] = {}
    no_resueltas: dict[str, dict] = {}
    for campo, texto in recorrer_textos(registro):
        for cita in extraer_citas(texto, campo):
            resueltos, motivo = resolver_cita(cita, catalogo, ejercicios, convenios)
            for enlace in resueltos:
                enlaces.setdefault(_clave_enlace(enlace), enlace)
            if motivo:
                no_resueltas.setdefault(
                    f"{cita.texto.lower()}|{cita.sigla or ''}",
                    {
                        "texto_citado": cita.texto,
                        "sigla": cita.sigla,
                        "campo": campo,
                        "motivo": motivo,
                    },
                )

    ordenados = sorted(enlaces.values(), key=lambda e: (e.slug, e.apartado or "", e.campo))
    anacronismo = (
        bool(ejercicios)
        and max(ejercicios) < PRIMER_EJERCICIO_LIRPF
        and any(e.boe_id == NORMA_RESIDENCIA_DESDE_2007 for e in ordenados)
    )
    return {
        "archivo": registro.get("archivo"),
        "roj": (registro.get("identificadores") or {}).get("ROJ"),
        "ejercicios": ejercicios,
        "pais_cdi": registro.get("pais_CDI_aplicado"),
        "preceptos": [
            {
                "slug": e.slug,
                "boe_id": e.boe_id,
                "bloque_id": e.bloque_id,
                "apartado": e.apartado,
                "certeza": e.certeza,
                "texto_citado": e.texto_citado,
                "campo": e.campo,
                "redaccion_aplicable": e.redaccion_aplicable,
            }
            for e in ordenados
        ],
        "citas_no_resueltas": sorted(no_resueltas.values(), key=lambda c: c["texto_citado"]),
        "avisos": (
            [
                "Cita la Ley 35/2006 en un caso cuyo último ejercicio es anterior a 2007, "
                "cuando regía el texto refundido de 2004. Puede ser abreviatura del "
                "análisis o un error: no se corrige aquí."
            ]
            if anacronismo
            else []
        ),
    }
