"""Proyección pública de un caso canónico v3, con allowlist campo a campo.

El frontend **no** debe recibir el caso completo. Un caso trae procedencia del
prompt, identificadores de ejecución y notas internas de revisión que no son
contenido publicable, y sobre todo: añadir mañana un campo al schema canónico no
puede publicarlo por accidente. Por eso la proyección declara campo a campo lo
que sale, en vez de copiar y borrar.

**El estado de publicación se calcula, no se declara.** Sale de la revisión
jurídica de cada elemento proyectado:

- `internal_preview`: hay algún elemento que no está `HUMAN_APPROVED`. Es
  renderizable en local y en un Deploy Preview, siempre `noindex` y fuera del
  sitemap.
- `publishable`: todos los elementos proyectados llevan aprobación humana.

Hoy los 106 casos agregan 1.620 elementos `AGENT_REVIEWED` y ninguno
`HUMAN_APPROVED`, así que los 67 candidatos salen `internal_preview`. Un flag de
frontend no puede ascender ninguno: el estado viaja en el manifiesto con hash.

El tercer estado, `published`, lo concede el gate editorial por lote y vive en
el manifiesto (`export_public_judgments.py`), no en el caso.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from jurisdiction_roles import Rol, derivar_roles
from treaty_relations import contraparte_de, instrumento_vigente

SCHEMA_VERSION = "residenciafiscal-public-judgment/1"

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]

# Revisión jurídica que exige el gate de publicación (JURISPRUDENCE_PHASE_E0).
REVISION_APROBADA = "HUMAN_APPROVED"

# Roles del sidecar que autorizan a enlazar públicamente una jurisdicción desde
# la ficha. `mentioned_only` no: es el residual, y con él la saga del ICEX
# publicaría 31 sentencias «sobre» el país de destino de la beca.
ROLES_ENLAZABLES = frozenset({Rol.RESIDENCE_CLAIMED, Rol.TREATY_APPLIED})


class EstadoPublicacion(StrEnum):
    INTERNAL_PREVIEW = "internal_preview"
    PUBLISHABLE = "publishable"


class ModeloPublico(BaseModel):
    """Contrato cerrado y serializado en camelCase, como el resto de `public/data`."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RevisionPublica(ModeloPublico):
    """Estado de revisión, sin las notas internas del pipeline."""

    legal: str
    technical: str
    reviewed_at: str | None = None
    reviewed_by: str | None = None


class ProcedenciaPublica(ModeloPublico):
    """Quién generó el análisis. Lo exige §6.3: la procedencia es visible.

    No incluye `prompt_sha256` ni `run_id`: identifican una ejecución interna y
    no aportan nada a quien lee la ficha.
    """

    producer: str
    model_id: str
    generated_at: str


class IdentidadPublica(ModeloPublico):
    """Datos primarios de la sentencia. Son hechos registrales, no análisis."""

    judgment_id: Slug
    roj: str
    ecli: str
    court: str
    chamber: str | None = None
    decision_date: str
    tax_years: tuple[int, ...]
    page_count: int
    source_file: str
    source_sha256: Sha256
    is_tax_residence_case: bool
    provenance: ProcedenciaPublica
    review: RevisionPublica


class FragmentoPublico(ModeloPublico):
    """Trozo literal del PDF, con su página física y su etiqueta impresa."""

    page_index: int
    printed_page: str | None
    verbatim_text: str


class AnclajePublico(ModeloPublico):
    """Lo único de la ficha que reproduce texto judicial."""

    anchor_id: str
    purpose: str
    fidelity: str
    source_sha256: Sha256
    fragments: tuple[FragmentoPublico, ...]
    review: RevisionPublica


class DocumentoExtranjeroPublico(ModeloPublico):
    document_type: str
    nature: str | None = None
    issuing_authority: str | None = None
    jurisdiction: str | None = None
    tax_scope: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    probative_effect: str | None = None
    defects: tuple[str, ...] = ()


class PruebaPublica(ModeloPublico):
    evidence_id: str
    category: str
    subtype: str | None = None
    description: str
    offered_by: str
    assessment: str
    assessment_reason: str | None = None
    role: str | None = None
    probative_purpose: str | None = None
    foreign_document: DocumentoExtranjeroPublico | None = None
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class HechoPublico(ModeloPublico):
    fact_id: str
    category: str
    description: str
    subject_role: str | None = None
    asserted_by: str | None = None
    procedural_status: str | None = None
    country: str | None = None
    place: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    tax_years: tuple[int, ...] = ()
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class NormaPublica(ModeloPublico):
    legal_rule_id: str
    rule_type: str
    citation: str
    proposition: str
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class PasoCargaPublico(ModeloPublico):
    step_id: str
    sequence: int
    initial_bearer: str
    fact_to_prove: str
    response_required: str | None = None
    shifts_to: str | None = None
    conclusion: str | None = None
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class PeriodoPublico(ModeloPublico):
    period_id: str
    country: str | None = None
    classification: str
    start_date: str | None = None
    end_date: str | None = None
    day_count: int | None = None
    counted_for183_day_rule: bool | None = Field(default=None, alias="countedFor183DayRule")
    determined_by: str | None = None
    calculation_method: str | None = None
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class PasoConvenioPublico(ModeloPublico):
    """Un paso del desempate del convenio (vivienda, centro de intereses…).

    Estaba proyectado como `dict` crudo y por ahí se colaban las notas internas
    de revisión: el agujero exacto que la allowlist existe para cerrar.
    """

    step_id: str
    sequence: int
    criterion: str
    applied: bool | None = None
    conclusion: str | None = None
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class AnalisisConvenioPublico(ModeloPublico):
    treaty_analysis_id: str
    treaty_citation: str
    countries: tuple[str, ...] = ()
    dual_residence_established: bool | None = None
    result_country: str | None = None
    steps: tuple[PasoConvenioPublico, ...] = ()
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class DeterminacionPublica(ModeloPublico):
    spanish_residence: str
    other_country: str | None = None
    non_resident_from: str | None = None
    tax_years: tuple[int, ...] = ()


class FalloPublico(ModeloPublico):
    holding_id: str
    outcome: str
    conclusion: str
    decisive_reasoning: str | None = None
    consequences: tuple[str, ...] = ()
    residence_determination: DeterminacionPublica | None = None
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class CuestionPublica(ModeloPublico):
    """Una cuestión jurídica con todo lo que el post publica bajo ella."""

    issue_id: str
    issue_type: str
    question: str
    criterion_ids: tuple[str, ...] = ()
    holding: FalloPublico | None = None
    facts: tuple[HechoPublico, ...] = ()
    evidence: tuple[PruebaPublica, ...] = ()
    legal_rules: tuple[NormaPublica, ...] = ()
    burden_of_proof: tuple[PasoCargaPublico, ...] = ()
    presence_periods: tuple[PeriodoPublico, ...] = ()
    treaty_analyses: tuple[AnalisisConvenioPublico, ...] = ()
    anchor_ids: tuple[str, ...] = ()
    review: RevisionPublica


class JurisdiccionPublica(ModeloPublico):
    """Jurisdicción con papel tipado y el convenio que regía el caso.

    Solo salen los roles que autorizan enlace. Lo que únicamente aparece en
    `judgment.countries` no llega aquí: el enlazado se construye contra roles
    tipados, nunca contra el campo en bruto.

    Los convenios son **los que rigen los ejercicios enjuiciados**, no el
    vigente hoy. Un caso de 2011 con el Reino Unido aplica el convenio de 1975,
    y enlazar el de 2013 publicaría derecho que entonces no existía. Son varios
    cuando el caso cruza el cambio de convenio, como los ejercicios 2013-2014.
    """

    code: str
    roles: tuple[str, ...]
    treaty_boe_ids: tuple[str, ...] = ()


class PublicJudgment(ModeloPublico):
    """Lo que puede salir del corpus hacia la web, y nada más."""

    schema_version: Literal["residenciafiscal-public-judgment/1"]
    jurisdiction: Literal["es"]
    publication_state: EstadoPublicacion
    judgment: IdentidadPublica
    issues: tuple[CuestionPublica, ...]
    anchors: tuple[AnclajePublico, ...]
    jurisdictions: tuple[JurisdiccionPublica, ...] = ()


def _revision(elemento: dict) -> RevisionPublica:
    revision = elemento.get("review") or {}
    return RevisionPublica(
        legal=revision.get("legal", "UNREVIEWED"),
        technical=revision.get("technical", "GENERATED"),
        reviewed_at=revision.get("reviewed_at"),
        reviewed_by=revision.get("reviewed_by"),
    )


def _por_cuestion(elementos: list[dict], issue_id: str, campo: str = "issue_ids") -> list[dict]:
    return [elemento for elemento in elementos if issue_id in (elemento.get(campo) or ())]


def _convenios_del_caso(code: str, ejercicios: tuple[int, ...]) -> tuple[str, ...]:
    """Convenios que rigieron esa relación en los ejercicios enjuiciados.

    Sin ejercicios no se declara ninguno: elegir el vigente sería adivinar, y la
    consecuencia de acertar mal es enlazar la sentencia con el derecho de otra
    época.
    """
    identificadores = []
    for ejercicio in ejercicios:
        instrumento = instrumento_vigente(code, ejercicio)
        if instrumento is not None:
            identificadores.append(instrumento.boe_id)
    return tuple(dict.fromkeys(identificadores))


def _jurisdicciones(caso: dict) -> tuple[JurisdiccionPublica, ...]:
    sidecar = derivar_roles(caso)
    ejercicios = tuple(caso["judgment"].get("tax_years") or ())
    publicas = []
    for entrada in sidecar.jurisdictions:
        roles = tuple(rol for rol in entrada.roles if rol in ROLES_ENLAZABLES)
        if not roles:
            continue
        publicas.append(
            JurisdiccionPublica(
                code=entrada.code,
                roles=tuple(str(rol) for rol in roles),
                treaty_boe_ids=_convenios_del_caso(entrada.code, ejercicios),
            )
        )
    return tuple(publicas)


def _cuestion(caso: dict, issue: dict) -> CuestionPublica:
    issue_id = issue["issue_id"]
    holdings = [h for h in caso.get("holdings", ()) if h.get("issue_id") == issue_id]

    return CuestionPublica(
        issue_id=issue_id,
        issue_type=issue["issue_type"],
        question=issue["question"],
        criterion_ids=tuple(issue.get("criterion_ids") or ()),
        holding=_fallo(holdings[0]) if holdings else None,
        facts=tuple(_hecho(f) for f in _por_cuestion(list(caso.get("facts", ())), issue_id)),
        evidence=tuple(
            _prueba(e) for e in _por_cuestion(list(caso.get("evidence_findings", ())), issue_id)
        ),
        legal_rules=tuple(
            _norma(r) for r in _por_cuestion(list(caso.get("legal_rules", ())), issue_id)
        ),
        burden_of_proof=tuple(
            _paso(p)
            for p in sorted(
                _por_cuestion(list(caso.get("burden_of_proof_steps", ())), issue_id),
                key=lambda paso: paso.get("sequence", 0),
            )
        ),
        presence_periods=tuple(
            _periodo(p) for p in _por_cuestion(list(caso.get("presence_periods", ())), issue_id)
        ),
        treaty_analyses=tuple(
            _convenio(t)
            for t in _por_cuestion(
                list(caso.get("treaty_analyses", ())), issue_id, campo="domestic_law_issue_ids"
            )
        ),
        anchor_ids=tuple(issue.get("anchor_ids") or ()),
        review=_revision(issue),
    )


def _fallo(holding: dict) -> FalloPublico:
    determinacion = holding.get("residence_determination")
    return FalloPublico(
        holding_id=holding["holding_id"],
        outcome=holding["outcome"],
        conclusion=holding["conclusion"],
        decisive_reasoning=holding.get("decisive_reasoning"),
        consequences=tuple(holding.get("consequences") or ()),
        residence_determination=(
            DeterminacionPublica(
                spanish_residence=determinacion["spanish_residence"],
                other_country=determinacion.get("other_country"),
                non_resident_from=determinacion.get("non_resident_from"),
                tax_years=tuple(determinacion.get("tax_years") or ()),
            )
            if determinacion
            else None
        ),
        anchor_ids=tuple(holding.get("anchor_ids") or ()),
        review=_revision(holding),
    )


def _hecho(hecho: dict) -> HechoPublico:
    return HechoPublico(
        fact_id=hecho["fact_id"],
        category=hecho["category"],
        description=hecho["description"],
        subject_role=hecho.get("subject_role"),
        asserted_by=hecho.get("asserted_by"),
        procedural_status=hecho.get("procedural_status"),
        country=hecho.get("country"),
        place=hecho.get("place"),
        start_date=hecho.get("start_date"),
        end_date=hecho.get("end_date"),
        tax_years=tuple(hecho.get("tax_years") or ()),
        anchor_ids=tuple(hecho.get("anchor_ids") or ()),
        review=_revision(hecho),
    )


def _prueba(evidencia: dict) -> PruebaPublica:
    documento = evidencia.get("foreign_document")
    return PruebaPublica(
        evidence_id=evidencia["evidence_id"],
        category=evidencia["category"],
        subtype=evidencia.get("subtype"),
        description=evidencia["description"],
        offered_by=evidencia["offered_by"],
        assessment=evidencia["assessment"],
        assessment_reason=evidencia.get("assessment_reason"),
        role=evidencia.get("role"),
        probative_purpose=evidencia.get("probative_purpose"),
        foreign_document=(
            DocumentoExtranjeroPublico(
                document_type=documento["document_type"],
                nature=documento.get("nature"),
                issuing_authority=documento.get("issuing_authority"),
                jurisdiction=documento.get("jurisdiction"),
                tax_scope=documento.get("tax_scope"),
                period_start=documento.get("period_start"),
                period_end=documento.get("period_end"),
                probative_effect=documento.get("probative_effect"),
                defects=tuple(documento.get("defects") or ()),
            )
            if documento
            else None
        ),
        anchor_ids=tuple(evidencia.get("anchor_ids") or ()),
        review=_revision(evidencia),
    )


def _norma(regla: dict) -> NormaPublica:
    return NormaPublica(
        legal_rule_id=regla["legal_rule_id"],
        rule_type=regla["rule_type"],
        citation=regla["citation"],
        proposition=regla["proposition"],
        anchor_ids=tuple(regla.get("anchor_ids") or ()),
        review=_revision(regla),
    )


def _paso(paso: dict) -> PasoCargaPublico:
    return PasoCargaPublico(
        step_id=paso["step_id"],
        sequence=paso["sequence"],
        initial_bearer=paso["initial_bearer"],
        fact_to_prove=paso["fact_to_prove"],
        response_required=paso.get("response_required"),
        shifts_to=paso.get("shifts_to"),
        conclusion=paso.get("conclusion"),
        anchor_ids=tuple(paso.get("anchor_ids") or ()),
        review=_revision(paso),
    )


def _periodo(periodo: dict) -> PeriodoPublico:
    return PeriodoPublico(
        period_id=periodo["period_id"],
        country=periodo.get("country"),
        classification=periodo["classification"],
        start_date=periodo.get("start_date"),
        end_date=periodo.get("end_date"),
        day_count=periodo.get("day_count"),
        counted_for183_day_rule=periodo.get("counted_for_183_day_rule"),
        determined_by=periodo.get("determined_by"),
        calculation_method=periodo.get("calculation_method"),
        anchor_ids=tuple(periodo.get("anchor_ids") or ()),
        review=_revision(periodo),
    )


def _convenio(analisis: dict) -> AnalisisConvenioPublico:
    return AnalisisConvenioPublico(
        treaty_analysis_id=analisis["treaty_analysis_id"],
        treaty_citation=analisis["treaty_citation"],
        countries=tuple(analisis.get("countries") or ()),
        dual_residence_established=analisis.get("dual_residence_established"),
        result_country=analisis.get("result_country"),
        steps=tuple(
            PasoConvenioPublico(
                step_id=paso["step_id"],
                sequence=paso["sequence"],
                criterion=paso["criterion"],
                applied=paso.get("applied"),
                conclusion=paso.get("conclusion"),
                anchor_ids=tuple(paso.get("anchor_ids") or ()),
                review=_revision(paso),
            )
            for paso in sorted(
                analisis.get("steps") or (), key=lambda paso: paso.get("sequence", 0)
            )
        ),
        anchor_ids=tuple(analisis.get("anchor_ids") or ()),
        review=_revision(analisis),
    )


def _anclaje(anclaje: dict) -> AnclajePublico:
    return AnclajePublico(
        anchor_id=anclaje["anchor_id"],
        purpose=anclaje["purpose"],
        fidelity=anclaje["fidelity"],
        source_sha256=anclaje["source_sha256"],
        fragments=tuple(
            FragmentoPublico(
                page_index=fragmento["page_index"],
                printed_page=fragmento.get("printed_page"),
                # Subcadena exacta del verbatim: no se recorta, une ni reformatea.
                verbatim_text=fragmento["verbatim_text"],
            )
            for fragmento in anclaje.get("fragments") or ()
        ),
        review=_revision(anclaje),
    )


def _anclajes_usados(cuestiones: tuple[CuestionPublica, ...]) -> set[str]:
    usados: set[str] = set()
    for cuestion in cuestiones:
        usados.update(cuestion.anchor_ids)
        for grupo in (
            cuestion.facts,
            cuestion.evidence,
            cuestion.legal_rules,
            cuestion.burden_of_proof,
            cuestion.presence_periods,
            cuestion.treaty_analyses,
        ):
            for elemento in grupo:
                usados.update(elemento.anchor_ids)
        # Un paso del desempate puede citar un anclaje que su análisis padre no
        # repite. Sin recorrerlos, la ficha publicaría la conclusión del paso y
        # se quedaría sin el extracto literal que la sostiene.
        for analisis in cuestion.treaty_analyses:
            for paso in analisis.steps:
                usados.update(paso.anchor_ids)
        if cuestion.holding:
            usados.update(cuestion.holding.anchor_ids)
    return usados


def estado_de_publicacion(proyeccion: PublicJudgment) -> EstadoPublicacion:
    """Estado calculado a partir de la revisión de lo que se publica.

    Se mira lo **proyectado**, no el caso entero: un elemento interno sin
    aprobar no debe bloquear una ficha que no lo publica, y a la inversa, un
    elemento publicado sin aprobación humana la bloquea siempre.
    """
    revisiones = [proyeccion.judgment.review]
    for cuestion in proyeccion.issues:
        revisiones.append(cuestion.review)
        if cuestion.holding:
            revisiones.append(cuestion.holding.review)
        for grupo in (
            cuestion.facts,
            cuestion.evidence,
            cuestion.legal_rules,
            cuestion.burden_of_proof,
            cuestion.presence_periods,
            cuestion.treaty_analyses,
        ):
            revisiones.extend(elemento.review for elemento in grupo)
        # Cada paso del desempate se publica con su propia conclusión jurídica y
        # lleva revisión propia: aprobar el análisis padre no aprueba sus pasos.
        for analisis in cuestion.treaty_analyses:
            revisiones.extend(paso.review for paso in analisis.steps)
    revisiones.extend(anclaje.review for anclaje in proyeccion.anchors)

    if all(revision.legal == REVISION_APROBADA for revision in revisiones):
        return EstadoPublicacion.PUBLISHABLE
    return EstadoPublicacion.INTERNAL_PREVIEW


def proyectar(caso: dict) -> PublicJudgment:
    """Proyección pública de un caso canónico, con su estado ya calculado."""
    judgment = caso["judgment"]
    provenance = judgment.get("analysis_provenance") or {}

    cuestiones = tuple(_cuestion(caso, issue) for issue in caso.get("legal_issues", ()))
    usados = _anclajes_usados(cuestiones)
    anclajes = tuple(
        _anclaje(anclaje)
        for anclaje in caso.get("source_anchors", ())
        if anclaje["anchor_id"] in usados
    )

    proyeccion = PublicJudgment(
        schema_version=SCHEMA_VERSION,
        jurisdiction="es",
        # Provisional: lo recalcula la línea siguiente sobre la proyección ya
        # construida, que es lo único que se publica.
        publication_state=EstadoPublicacion.INTERNAL_PREVIEW,
        judgment=IdentidadPublica(
            judgment_id=judgment["judgment_id"],
            roj=judgment["roj"],
            ecli=judgment["ecli"],
            court=judgment["court"],
            chamber=judgment["chamber"],
            decision_date=judgment["decision_date"],
            tax_years=tuple(judgment.get("tax_years") or ()),
            page_count=judgment["page_count"],
            source_file=judgment["source_file"],
            source_sha256=judgment["source_sha256"],
            is_tax_residence_case=judgment["is_tax_residence_case"],
            provenance=ProcedenciaPublica(
                producer=provenance.get("producer", "desconocido"),
                model_id=provenance.get("model_id", "desconocido"),
                generated_at=provenance.get("generated_at", ""),
            ),
            review=_revision(judgment),
        ),
        issues=cuestiones,
        anchors=anclajes,
        jurisdictions=_jurisdicciones(caso),
    )
    return proyeccion.model_copy(update={"publication_state": estado_de_publicacion(proyeccion)})


def preceptos_citados(proyeccion: PublicJudgment) -> tuple[str, ...]:
    """Convenios que la ficha puede enlazar, por su identificador del BOE.

    Salen de las jurisdicciones con rol tipado, no de las citas en texto libre:
    resolver «art. 4.2 CDI» a una norma es trabajo del enlazador de citas, y
    aquí adivinarlo publicaría el convenio de otro Estado.
    """
    identificadores = [
        boe_id
        for jurisdiccion in proyeccion.jurisdictions
        for boe_id in jurisdiccion.treaty_boe_ids
        if contraparte_de(boe_id)
    ]
    return tuple(dict.fromkeys(identificadores))


def render_public_judgment(caso: dict) -> str:
    """Serializa la proyección de forma estable, para que regenerar no dé diff."""
    return (
        json.dumps(
            proyectar(caso).model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def render_public_judgment_json_schema() -> str:
    """Serializa el JSON Schema de la proyección de forma estable y legible."""
    return (
        json.dumps(
            PublicJudgment.model_json_schema(by_alias=True),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
