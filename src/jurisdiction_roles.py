"""Deriva de cada caso v3 qué papel juega en él cada jurisdicción.

Que un país aparezca en una sentencia no dice nada por sí solo: 31 de las 106
son la saga de becarios del ICEX, donde el país es el destino de la beca y no la
jurisdicción cuya residencia se discute. Publicar «N sentencias sobre X» sobre
ese recuento sería falso.

El papel sale por eso de **campos tipados del caso** —la determinación
residencial, el análisis de convenio, los periodos y eventos de presencia, los
hechos localizados y la jurisdicción emisora de un documento extranjero—, y cada
uno queda anotado con el campo del que procede. Lo que solo aparece en
`judgment.countries` se queda en `mentioned_only`, que es el residual y no
autoriza ningún enlace público.

Esto es un **sidecar**, no una edición del caso: los 106 casos generados no se
tocan a mano. A medio plazo estos papeles pasan al schema canónico siguiente.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from jurisdiction_normalization import normalizar_grafia_de_pais

SCHEMA_VERSION = "residenciafiscal-jurisdiction-roles/1"

CodigoJurisdiccion = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}(?:[a-z]{2})?$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Rol(StrEnum):
    """Papel de una jurisdicción en el caso, del más fuerte al residual."""

    # Su residencia fiscal es lo que se discute.
    RESIDENCE_CLAIMED = "residence_claimed"
    # Es parte del convenio que el tribunal aplica.
    TREATY_APPLIED = "treaty_applied"
    # Allí se sitúa un hecho, un periodo de presencia o el documento aportado.
    EVIDENCE_LOCATION = "evidence_location"
    # Aparece nombrada y ningún campo tipado le asigna papel.
    MENTIONED_ONLY = "mentioned_only"


ROLES_TIPADOS = frozenset({Rol.RESIDENCE_CLAIMED, Rol.TREATY_APPLIED, Rol.EVIDENCE_LOCATION})

# Orden canónico de salida: hace el fichero estable entre ejecuciones.
ORDEN_DE_ROLES = (
    Rol.RESIDENCE_CLAIMED,
    Rol.TREATY_APPLIED,
    Rol.EVIDENCE_LOCATION,
    Rol.MENTIONED_ONLY,
)


class ModeloSidecar(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RolJurisdiccional(ModeloSidecar):
    """Una jurisdicción del caso con sus papeles y su procedencia."""

    code: CodigoJurisdiccion
    roles: Annotated[tuple[Rol, ...], Field(min_length=1)]
    # Campos del caso que sostienen cada papel. Un rol sin procedencia es una
    # afirmación jurídica sin fuente, y el Gate A lo prohíbe.
    derived_from: Annotated[tuple[str, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validar_residual(self) -> Self:
        if Rol.MENTIONED_ONLY in self.roles and len(self.roles) > 1:
            raise ValueError(f"{self.code}: `mentioned_only` describe la ausencia de papel")
        return self


class SidecarRoles(ModeloSidecar):
    """Sidecar de una sentencia, atado a su fuente por el hash del PDF."""

    schema_version: Literal["residenciafiscal-jurisdiction-roles/1"]
    judgment_id: str
    source_sha256: Sha256
    jurisdictions: tuple[RolJurisdiccional, ...]

    @model_validator(mode="after")
    def validar_orden(self) -> Self:
        codigos = [entrada.code for entrada in self.jurisdictions]
        if len(codigos) != len(set(codigos)):
            raise ValueError(f"{self.judgment_id}: jurisdicción repetida")
        if codigos != sorted(codigos):
            raise ValueError(f"{self.judgment_id}: las entradas van ordenadas por código")
        return self


def _codigos(valor: object) -> tuple[str, ...]:
    """Códigos de un campo de país, o vacío si no hay valor."""
    if not valor:
        return ()
    return normalizar_grafia_de_pais(str(valor))


def _codigo_unico(valor: object) -> tuple[str, ...]:
    """Códigos de un campo que describe **una sola** jurisdicción.

    Varios `foreign_document.jurisdiction` del corpus traen copiado el valor de
    `judgment.countries` —«Israel;Brasil», el título de un convenio—, y una
    autoridad emisora no puede ser dos países. Cuando el valor resuelve a más de
    uno se descarta: preferimos perder un rol a inventarlo.
    """
    codigos = _codigos(valor)
    return codigos if len(codigos) == 1 else ()


def derivar_roles(caso: dict) -> SidecarRoles:
    """Sidecar de roles de un caso canónico v3."""
    judgment = caso["judgment"]
    anotaciones: dict[str, dict[Rol, set[str]]] = {}

    def anotar(codigos: tuple[str, ...], rol: Rol, origen: str) -> None:
        for code in codigos:
            anotaciones.setdefault(code, {}).setdefault(rol, set()).add(origen)

    for indice, holding in enumerate(caso.get("holdings", ())):
        determinacion = holding.get("residence_determination")
        if not determinacion:
            continue
        origen = f"holdings[{indice}].residence_determination"
        # La determinación versa siempre sobre la residencia española: es el
        # objeto del proceso aunque el fallo no llegue a decidirla.
        anotar(("es",), Rol.RESIDENCE_CLAIMED, f"{origen}.spanish_residence")
        anotar(
            _codigos(determinacion.get("other_country")),
            Rol.RESIDENCE_CLAIMED,
            f"{origen}.other_country",
        )

    for indice, analisis in enumerate(caso.get("treaty_analyses", ())):
        origen = f"treaty_analyses[{indice}]"
        for pais in analisis.get("countries") or ():
            anotar(_codigos(pais), Rol.TREATY_APPLIED, f"{origen}.countries")
        anotar(
            _codigos(analisis.get("result_country")),
            Rol.TREATY_APPLIED,
            f"{origen}.result_country",
        )

    for coleccion in ("facts", "presence_periods", "presence_events"):
        for indice, elemento in enumerate(caso.get(coleccion, ())):
            anotar(
                _codigos(elemento.get("country")),
                Rol.EVIDENCE_LOCATION,
                f"{coleccion}[{indice}].country",
            )

    for indice, evidencia in enumerate(caso.get("evidence_findings", ())):
        documento = evidencia.get("foreign_document")
        if not documento:
            continue
        anotar(
            _codigo_unico(documento.get("jurisdiction")),
            Rol.EVIDENCE_LOCATION,
            f"evidence_findings[{indice}].foreign_document.jurisdiction",
        )

    for pais in judgment.get("countries") or ():
        for code in _codigos(pais):
            anotaciones.setdefault(code, {}).setdefault(Rol.MENTIONED_ONLY, set()).add(
                "judgment.countries"
            )

    entradas = []
    for code in sorted(anotaciones):
        por_rol = anotaciones[code]
        tipados = {rol: origenes for rol, origenes in por_rol.items() if rol in ROLES_TIPADOS}
        elegidos = tipados or por_rol
        roles = tuple(rol for rol in ORDEN_DE_ROLES if rol in elegidos)
        origenes = sorted({origen for rol in roles for origen in elegidos[rol]})
        entradas.append(RolJurisdiccional(code=code, roles=roles, derived_from=tuple(origenes)))

    return SidecarRoles(
        schema_version=SCHEMA_VERSION,
        judgment_id=judgment["judgment_id"],
        source_sha256=judgment["source_sha256"],
        jurisdictions=tuple(entradas),
    )


def render_sidecar(caso: dict) -> str:
    """Serializa el sidecar de forma estable, para que regenerar no dé diff."""
    sidecar = derivar_roles(caso)
    return (
        json.dumps(
            sidecar.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def render_jurisdiction_roles_json_schema() -> str:
    """Serializa el JSON Schema del sidecar de forma estable y legible."""
    return (
        json.dumps(
            SidecarRoles.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_jurisdiction_roles_json_schema(destination: Path) -> Path:
    """Escribe el schema generado en un destino explícito."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_jurisdiction_roles_json_schema(), encoding="utf-8")
    return destination
