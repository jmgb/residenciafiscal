"""Catálogo canónico de jurisdicciones: la única clave de cruce del proyecto.

Antes, el nombre de un país vivía duplicado en tres sitios editables —las rutas
del frontend, los metadatos de las fichas de precepto y una tabla de convenios
dentro del enlazador de citas— y nada impedía que divergieran. Aquí hay una sola
fuente; los demás consumidores reciben proyecciones generadas.

**`code` es la clave; `slug` es presentación.** El código ISO cruza el catálogo
con `normativa/<iso>/`, con `countryRoutes.json` y con el corpus. El slug decide
la URL y puede cambiar mediante una migración; por eso nunca se usa para enlazar
artefactos, y la construcción de rutas vive en `path_de` y en ningún otro sitio.

Los alias **solo normalizan grafías**. No deciden si una jurisdicción es parte de
la controversia, el lugar de una prueba o una simple mención: ese papel jurídico
lo asigna el sidecar de roles a partir de campos tipados del caso.
"""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CATALOGO_JSON = Path(__file__).with_name("jurisdiction_catalog.json")
SCHEMA_VERSION = "residenciafiscal-jurisdictions/1"

CodigoJurisdiccion = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}(?:[a-z]{2})?$")]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
TextoNoVacio = Annotated[str, StringConstraints(min_length=1)]


class ModeloCatalogo(BaseModel):
    """Configuración común: contrato cerrado e inmutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Jurisdiccion(ModeloCatalogo):
    """Una jurisdicción con su código estándar, su nombre y sus grafías."""

    code: CodigoJurisdiccion
    # ISO 3166-3 existe para los Estados que dejaron de existir. Checoslovaquia
    # y la URSS firmaron convenios que el corpus todavía publica, así que el
    # catálogo los necesita; inventarles un alfa-2 sería fabricar una clave que
    # ningún otro sistema reconoce.
    code_type: Literal["iso-3166-1-alpha-2", "iso-3166-3-alpha-4"]
    name: TextoNoVacio
    slug: Slug
    aliases: tuple[TextoNoVacio, ...] = ()

    @model_validator(mode="after")
    def validar_longitud_del_codigo(self) -> Self:
        esperada = 2 if self.code_type == "iso-3166-1-alpha-2" else 4
        if len(self.code) != esperada:
            raise ValueError(f"{self.code}: un {self.code_type} tiene {esperada} letras")
        return self


class CatalogoJurisdicciones(ModeloCatalogo):
    """Documento versionado del catálogo."""

    schema_version: Literal["residenciafiscal-jurisdictions/1"]
    jurisdictions: Annotated[tuple[Jurisdiccion, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validar_unicidad(self) -> Self:
        for campo in ("code", "slug"):
            valores = [getattr(j, campo) for j in self.jurisdictions]
            repetidos = sorted({v for v in valores if valores.count(v) > 1})
            if repetidos:
                raise ValueError(f"{campo} repetido en el catálogo: {', '.join(repetidos)}")

        vistas: dict[str, str] = {}
        for jurisdiccion in self.jurisdictions:
            for grafia in (jurisdiccion.name, jurisdiccion.slug, *jurisdiccion.aliases):
                clave = normalizar_grafia(grafia)
                anterior = vistas.get(clave)
                if anterior is not None and anterior != jurisdiccion.code:
                    raise ValueError(
                        f"la grafía «{grafia}» resolvería a {anterior} y a {jurisdiccion.code}"
                    )
                vistas[clave] = jurisdiccion.code

        ordenado = sorted(self.jurisdictions, key=lambda j: j.code)
        if list(self.jurisdictions) != ordenado:
            raise ValueError("el catálogo se versiona ordenado por `code`")
        return self


def normalizar_grafia(texto: str) -> str:
    """Forma comparable de un nombre: sin tildes, sin puntos y en minúscula.

    No se usa NFKC: aquí no hay texto legal, pero la regla del proyecto es no
    acostumbrarse a normalizaciones que en el corpus normativo convertirían
    `1.º` en `1.o`. NFD + descarte de diacríticos hace justo lo necesario.
    """
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_tildes.replace(".", "").split())


@lru_cache(maxsize=1)
def cargar_catalogo(ruta: Path | None = None) -> dict[str, Jurisdiccion]:
    """Catálogo indexado por código, validado contra su contrato."""
    origen = ruta or CATALOGO_JSON
    documento = CatalogoJurisdicciones.model_validate_json(origen.read_text(encoding="utf-8"))
    return {j.code: j for j in documento.jurisdictions}


@lru_cache(maxsize=1)
def _indice_de_grafias() -> dict[str, Jurisdiccion]:
    indice: dict[str, Jurisdiccion] = {}
    for jurisdiccion in cargar_catalogo().values():
        for grafia in (jurisdiccion.name, jurisdiccion.slug, *jurisdiccion.aliases):
            indice[normalizar_grafia(grafia)] = jurisdiccion
    return indice


def resolver(texto: str) -> Jurisdiccion | None:
    """Jurisdicción que corresponde a una grafía completa, o `None`.

    La comparación es por igualdad de la grafía normalizada, nunca por
    subcadena: buscar «Guinea» dentro de «Guinea Ecuatorial» —o «España» dentro
    de «Nueva España»— produciría enlaces falsos, que es exactamente el riesgo
    que este catálogo existe para eliminar.
    """
    clave = normalizar_grafia(texto)
    return _indice_de_grafias().get(clave) if clave else None


def path_de(code: str) -> str:
    """Ruta pública de la jurisdicción. Única construcción de URL del proyecto.

    Centralizarla es lo que permite migrar el esquema de URL —o añadir un
    prefijo si algún día hay más de un idioma— sin buscar concatenaciones
    sueltas por todo el repositorio.
    """
    return f"/{cargar_catalogo()[code].slug}"


def render_jurisdictions_json_schema() -> str:
    """Serializa el JSON Schema del catálogo de forma estable y legible."""
    return (
        json.dumps(
            CatalogoJurisdicciones.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_jurisdictions_json_schema(destination: Path) -> Path:
    """Escribe el schema generado en un destino explícito."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_jurisdictions_json_schema(), encoding="utf-8")
    return destination
