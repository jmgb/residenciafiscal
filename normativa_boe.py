"""Parseo del XML de legislación consolidada del BOE.

Determinista y sin LLM, igual que `pdf_page_extraction.py` para las sentencias:
aquí el texto legal se lee de una fuente ya estructurada por el propio BOE, así
que no hay extracción heurística ni verificación difusa que hacer.

**Invariante:** el texto de un precepto no se reescribe, corrige ni parafrasea.
La única transformación admitida es de formato: colapsar espacios en blanco
(incluido el espacio duro `\\xa0` que el BOE usa en las rúbricas) y separar los
párrafos. Las notas al pie del BOE —«Redactado conforme a…», «Se modifica por…»—
son anotación editorial, no articulado, y se devuelven en un campo aparte.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# Clases de <p> que el BOE usa para sus propias notas editoriales.
CLASES_NOTA = ("nota_pie", "nota_pie_2", "nota_pie_3")

# Rúbrica de un precepto: «Artículo 9. Contribuyentes que tienen su residencia…».
RUBRICA = re.compile(
    r"^(?P<designacion>(?:Artículo|Disposición|Capítulo|Título)[^.]*?)\.\s*(?P<epigrafe>.*)$"
)


def normalizar_espacios(texto: str) -> str:
    """Colapsa cualquier espacio en blanco a un espacio simple.

    `\\s` en Python ya cubre el espacio duro `\\xa0` que el BOE inserta entre
    «Artículo» y su número, y el espacio EM que usa tras los ordinales. Es una
    transformación de formato: no altera ningún carácter del precepto.

    **No se normaliza a NFKC.** Esa forma convierte los ordinales `1.º` y `2.ª`
    en `1.o` y `2.a`, que es exactamente reescribir el texto legal: el art. 72
    LIRPF y el art. 106 LGT los usan al citar otros preceptos.
    """
    return re.sub(r"\s+", " ", texto).strip()


@dataclass(frozen=True)
class VersionPrecepto:
    """Una redacción del bloque, con la fecha desde la que estuvo vigente."""

    id_norma: str
    fecha_publicacion: str | None
    fecha_vigencia: str | None
    parrafos: tuple[str, ...]
    notas_boe: tuple[str, ...]
    tiene_tabla: bool

    @property
    def texto(self) -> str:
        return "\n\n".join(self.parrafos)


@dataclass(frozen=True)
class BloqueNorma:
    """Un bloque del texto consolidado: precepto, encabezado, preámbulo o firma."""

    bloque_id: str
    tipo: str
    titulo: str
    versiones: tuple[VersionPrecepto, ...]

    @property
    def version_vigente(self) -> VersionPrecepto | None:
        """La redacción más reciente; el BOE las sirve en orden cronológico."""
        return self.versiones[-1] if self.versiones else None

    @property
    def rubrica(self) -> str:
        """Primer párrafo de la redacción vigente: «Artículo 9. Contribuyentes…»."""
        vigente = self.version_vigente
        return vigente.parrafos[0] if vigente and vigente.parrafos else ""

    @property
    def epigrafe(self) -> str:
        """Nombre del precepto sin su designación, o cadena vacía si no lo tiene."""
        match = RUBRICA.match(self.rubrica)
        return match.group("epigrafe").rstrip(".").strip() if match else ""

    @property
    def texto_completo(self) -> str:
        """Todas las redacciones concatenadas, para buscar dentro del bloque."""
        return "\n\n".join(v.texto for v in self.versiones)


@dataclass(frozen=True)
class NormaBOE:
    """Norma consolidada con sus metadatos y sus bloques."""

    boe_id: str
    titulo: str
    rango: str | None
    fecha_disposicion: str | None
    fecha_publicacion: str | None
    fecha_vigencia: str | None
    vigencia_agotada: bool
    fecha_actualizacion_boe: str | None
    url_eli: str | None
    url_html_consolidada: str | None
    bloques: tuple[BloqueNorma, ...]

    def bloque(self, bloque_id: str) -> BloqueNorma | None:
        return next((b for b in self.bloques if b.bloque_id == bloque_id), None)

    @property
    def preceptos(self) -> tuple[BloqueNorma, ...]:
        return tuple(b for b in self.bloques if b.tipo == "precepto")


def _texto_elemento(elemento: ET.Element) -> str:
    """Texto plano de un `<p>`, incluyendo el de sus etiquetas anidadas."""
    return normalizar_espacios("".join(elemento.itertext()))


def _parsear_version(version: ET.Element) -> VersionPrecepto:
    parrafos: list[str] = []
    notas: list[str] = []
    for parrafo in version.iter("p"):
        texto = _texto_elemento(parrafo)
        if not texto:
            continue
        if parrafo.get("class", "") in CLASES_NOTA:
            notas.append(texto)
        else:
            parrafos.append(texto)
    return VersionPrecepto(
        id_norma=version.get("id_norma", ""),
        fecha_publicacion=version.get("fecha_publicacion"),
        fecha_vigencia=version.get("fecha_vigencia"),
        parrafos=tuple(parrafos),
        notas_boe=tuple(notas),
        tiene_tabla=version.find(".//td") is not None,
    )


def _campo(raiz: ET.Element, ruta: str) -> str | None:
    elemento = raiz.find(ruta)
    if elemento is None or elemento.text is None:
        return None
    return normalizar_espacios(elemento.text) or None


def parsear_norma(xml_metadatos: bytes, xml_texto: bytes) -> NormaBOE:
    """Construye una `NormaBOE` a partir de las dos respuestas de la API."""
    meta = ET.fromstring(xml_metadatos)
    texto = ET.fromstring(xml_texto)

    bloques = tuple(
        BloqueNorma(
            bloque_id=bloque.get("id", ""),
            tipo=bloque.get("tipo", ""),
            titulo=normalizar_espacios(bloque.get("titulo", "")),
            versiones=tuple(_parsear_version(v) for v in bloque.findall("version")),
        )
        for bloque in texto.iter("bloque")
    )

    boe_id = _campo(meta, ".//identificador")
    if not boe_id:
        raise ValueError("El XML de metadatos no declara <identificador>")

    return NormaBOE(
        boe_id=boe_id,
        titulo=_campo(meta, ".//titulo") or "",
        rango=_campo(meta, ".//rango"),
        fecha_disposicion=_campo(meta, ".//fecha_disposicion"),
        fecha_publicacion=_campo(meta, ".//fecha_publicacion"),
        fecha_vigencia=_campo(meta, ".//fecha_vigencia"),
        vigencia_agotada=(_campo(meta, ".//vigencia_agotada") or "N").upper() == "S",
        fecha_actualizacion_boe=_campo(meta, ".//fecha_actualizacion"),
        url_eli=_campo(meta, ".//url_eli"),
        url_html_consolidada=_campo(meta, ".//url_html_consolidada"),
        bloques=bloques,
    )


def cargar_norma(directorio: Path, boe_id: str) -> NormaBOE:
    """Lee `<boe_id>.meta.xml` y `<boe_id>.texto.xml` del directorio de fuentes."""
    metadatos = (directorio / f"{boe_id}.meta.xml").read_bytes()
    texto = (directorio / f"{boe_id}.texto.xml").read_bytes()
    return parsear_norma(metadatos, texto)


def _designacion_a_bloque_id(designacion: str) -> str:
    """«Artículo 9» -> `a9`, imitando los identificadores de la base consolidada."""
    numero = re.match(r"Artículo\s*(\d+)\s*(bis|ter)?", designacion, re.IGNORECASE)
    if numero:
        return "a" + numero.group(1) + (numero.group(2) or "")
    return re.sub(r"[^a-z0-9]+", "-", designacion.lower()).strip("-")


def parsear_norma_diario(xml_documento: bytes) -> NormaBOE:
    """Parsea el XML del diario del BOE, que es el formato de las normas derogadas.

    Una norma derogada sale de la base consolidada, así que solo queda su
    publicación original: una secuencia plana de `<p>` sin bloques. Los
    artículos se delimitan por los `<p class="articulo">`, que es exactamente la
    marca que usa el BOE para abrir cada precepto.
    """
    raiz = ET.fromstring(xml_documento)
    boe_id = _campo(raiz, ".//identificador")
    if not boe_id:
        raise ValueError("El XML del diario no declara <identificador>")

    bloques: list[BloqueNorma] = []
    designacion = ""
    parrafos: list[str] = []

    def cerrar() -> None:
        if not designacion:
            return
        bloques.append(
            BloqueNorma(
                bloque_id=_designacion_a_bloque_id(designacion),
                tipo="precepto",
                titulo=designacion,
                versiones=(
                    VersionPrecepto(
                        id_norma=boe_id,
                        fecha_publicacion=_campo(raiz, ".//fecha_publicacion"),
                        fecha_vigencia=_campo(raiz, ".//fecha_vigencia"),
                        parrafos=tuple(parrafos),
                        notas_boe=(),
                        tiene_tabla=False,
                    ),
                ),
            )
        )

    for parrafo in raiz.iter("p"):
        texto = _texto_elemento(parrafo)
        if not texto:
            continue
        if parrafo.get("class") == "articulo":
            cerrar()
            match = RUBRICA.match(texto)
            designacion = match.group("designacion") if match else texto
            parrafos = [texto]
        elif designacion:
            parrafos.append(texto)
    cerrar()

    return NormaBOE(
        boe_id=boe_id,
        titulo=_campo(raiz, ".//titulo") or "",
        rango=_campo(raiz, ".//rango"),
        fecha_disposicion=_campo(raiz, ".//fecha_disposicion"),
        fecha_publicacion=_campo(raiz, ".//fecha_publicacion"),
        fecha_vigencia=_campo(raiz, ".//fecha_vigencia"),
        vigencia_agotada=(_campo(raiz, ".//estatus_derogacion") or "N").upper() == "S",
        fecha_actualizacion_boe=raiz.get("fecha_actualizacion"),
        url_eli=None,
        url_html_consolidada=f"https://www.boe.es/buscar/doc.php?id={boe_id}",
        bloques=tuple(bloques),
    )


def cargar_norma_diario(directorio: Path, boe_id: str) -> NormaBOE:
    """Lee `<boe_id>.diario.xml`, el formato de las normas ya derogadas."""
    return parsear_norma_diario((directorio / f"{boe_id}.diario.xml").read_bytes())


def formatear_fecha(fecha: str | None) -> str | None:
    """`20070101` -> `2007-01-01`; devuelve la entrada si no tiene ese formato."""
    if not fecha:
        return None
    if re.fullmatch(r"\d{8}", fecha):
        return f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}"
    return fecha
