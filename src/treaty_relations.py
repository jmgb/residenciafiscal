"""Registro curado de las relaciones bilaterales de España, con sus periodos.

`treatyBoeId` en la página de país solo funciona mientras España sea la
contraparte implícita, y una tabla de rangos dentro del enlazador de citas no
puede responder a «qué convenio regía el ejercicio 2012». Aquí la relación es el
dato: `(jurisdicción fuente, contraparte, periodo) → norma`, y todo lo demás
—`treatyBoeId`, `CONVENIOS_POR_PAIS`, la ficha de precepto— pasa a ser una
proyección de este registro.

**La contraparte es curada, nunca deducida del título.** Los convenios escriben
el nombre del país de trece formas distintas, y un país equivocado publicaría el
derecho de otro Estado bajo el nombre correcto. La semilla es el bloque `paises`
de `normativaFichas.json`, que ya hizo ese trabajo a mano para las 97 fichas.

**El estado jurídico vive aquí, no en el `grupo` del manifiesto.** Ese grupo
describe de dónde se descarga la fuente —consolidado o diario—, no si el
convenio sigue aplicándose: Japón, Rumanía y China tienen dos convenios cada uno
que el índice consolidado del BOE no marca como sustituidos, porque la
derogación la produce el propio convenio nuevo.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

REGISTRO_JSON = Path(__file__).with_name("treaty_relations_es.json")
SCHEMA_VERSION = "residenciafiscal-treaty-relations/1"

IdentificadorBOE = Annotated[str, StringConstraints(pattern=r"^BOE-A-\d{4}-\d+$")]
CodigoJurisdiccion = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}(?:[a-z]{2})?$")]


class ModeloRegistro(BaseModel):
    """Configuración común: contrato cerrado e inmutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Instrumento(ModeloRegistro):
    """Un convenio concreto y los ejercicios fiscales en los que se aplica.

    Los rangos son de **ejercicio**, no de fecha de entrada en vigor: lo que
    decide qué convenio aplica una sentencia es el ejercicio enjuiciado, y la
    entrada en vigor casi nunca coincide con el 1 de enero.
    """

    boe_id: IdentificadorBOE
    status: Literal["current", "superseded"]
    effective_from_tax_year: int | None = None
    effective_to_tax_year: int | None = None
    replaced_by: IdentificadorBOE | None = None
    # Cita literal —o referencia— de la cláusula del convenio que fija el rango.
    # Sin ella, un rango es una afirmación jurídica sin fuente.
    source_note: str | None = None

    @model_validator(mode="after")
    def validar_rango(self) -> Self:
        desde, hasta = self.effective_from_tax_year, self.effective_to_tax_year
        if desde is not None and hasta is not None and desde > hasta:
            raise ValueError(f"{self.boe_id}: el rango de ejercicios está invertido")
        if self.status == "current" and self.effective_to_tax_year is not None:
            raise ValueError(f"{self.boe_id}: un convenio vigente no tiene ejercicio final")
        if self.status == "superseded" and self.replaced_by is None:
            raise ValueError(f"{self.boe_id}: un convenio sustituido declara su sucesor")
        return self

    def rige(self, ejercicio: int | None) -> bool:
        """¿Se aplica este instrumento a ese ejercicio?

        Sin ejercicio solo rige el instrumento sin rangos: no se elige uno «por
        defecto», porque escoger el moderno para un caso de 2010 enlazaría la
        sentencia con un convenio que entonces no existía.
        """
        if ejercicio is None:
            return self.effective_from_tax_year is None and self.effective_to_tax_year is None
        if self.effective_from_tax_year is not None and ejercicio < self.effective_from_tax_year:
            return False
        return not (
            self.effective_to_tax_year is not None and ejercicio > self.effective_to_tax_year
        )


class RelacionBilateral(ModeloRegistro):
    """Todos los convenios firmados con una contraparte, en orden cronológico."""

    counterpart: CodigoJurisdiccion
    instruments: Annotated[tuple[Instrumento, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validar_sucesion(self) -> Self:
        vigentes = [i for i in self.instruments if i.status == "current"]
        if len(vigentes) != 1:
            raise ValueError(f"{self.counterpart}: {len(vigentes)} instrumentos vigentes")
        if self.instruments[-1].status != "current":
            raise ValueError(f"{self.counterpart}: el vigente va el último")

        anterior: Instrumento | None = None
        for instrumento in self.instruments:
            if anterior is None:
                anterior = instrumento
                continue
            if anterior.replaced_by != instrumento.boe_id:
                raise ValueError(
                    f"{self.counterpart}: {anterior.boe_id} no declara como sucesor a "
                    f"{instrumento.boe_id}"
                )
            if (
                anterior.effective_to_tax_year is None
                or instrumento.effective_from_tax_year is None
                or instrumento.effective_from_tax_year != anterior.effective_to_tax_year + 1
            ):
                raise ValueError(
                    f"{self.counterpart}: hueco o solape entre {anterior.boe_id} y "
                    f"{instrumento.boe_id}"
                )
            anterior = instrumento
        return self


class RegistroRelaciones(ModeloRegistro):
    """Documento versionado de las relaciones de una jurisdicción fuente."""

    schema_version: Literal["residenciafiscal-treaty-relations/1"]
    # La jurisdicción que aporta el texto oficial. Cuando exista `normativa/pe/`,
    # tendrá su propio registro con su propio fichero.
    source_jurisdiction: CodigoJurisdiccion
    relations: Annotated[tuple[RelacionBilateral, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validar_unicidad(self) -> Self:
        contrapartes = [r.counterpart for r in self.relations]
        repetidas = sorted({c for c in contrapartes if contrapartes.count(c) > 1})
        if repetidas:
            raise ValueError(f"contraparte repetida: {', '.join(repetidas)}")
        if contrapartes != sorted(contrapartes):
            raise ValueError("el registro se versiona ordenado por contraparte")

        vistos: dict[str, str] = {}
        for relacion in self.relations:
            for instrumento in relacion.instruments:
                anterior = vistos.get(instrumento.boe_id)
                if anterior is not None:
                    raise ValueError(
                        f"{instrumento.boe_id} figura en {anterior} y en {relacion.counterpart}"
                    )
                vistos[instrumento.boe_id] = relacion.counterpart
        return self


@lru_cache(maxsize=1)
def cargar_relaciones(ruta: Path | None = None) -> dict[str, RelacionBilateral]:
    """Relaciones indexadas por contraparte, validadas contra su contrato."""
    origen = ruta or REGISTRO_JSON
    documento = RegistroRelaciones.model_validate_json(origen.read_text(encoding="utf-8"))
    return {relacion.counterpart: relacion for relacion in documento.relations}


def instrumentos_de(code: str) -> tuple[Instrumento, ...]:
    """Convenios firmados con esa contraparte, del más antiguo al vigente."""
    relacion = cargar_relaciones().get(code)
    return relacion.instruments if relacion else ()


def instrumento_vigente(code: str, ejercicio: int | None = None) -> Instrumento | None:
    """Convenio aplicable a ese ejercicio, o el vigente si no se indica ninguno."""
    instrumentos = instrumentos_de(code)
    if not instrumentos:
        return None
    if ejercicio is None:
        return next(i for i in instrumentos if i.status == "current")
    for instrumento in instrumentos:
        if instrumento.rige(ejercicio):
            return instrumento
    return None


@lru_cache(maxsize=1)
def _contrapartes_por_norma() -> dict[str, str]:
    return {
        instrumento.boe_id: code
        for code, relacion in cargar_relaciones().items()
        for instrumento in relacion.instruments
    }


def contraparte_de(boe_id: str) -> str | None:
    """Jurisdicción con la que España firmó ese convenio, o `None`."""
    return _contrapartes_por_norma().get(boe_id)


def render_treaty_relations_json_schema() -> str:
    """Serializa el JSON Schema del registro de forma estable y legible."""
    return (
        json.dumps(
            RegistroRelaciones.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_treaty_relations_json_schema(destination: Path) -> Path:
    """Escribe el schema generado en un destino explícito."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_treaty_relations_json_schema(), encoding="utf-8")
    return destination
