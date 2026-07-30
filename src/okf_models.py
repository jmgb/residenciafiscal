"""Modelo jurídico normalizado usado por los consumidores derivados del JSONL."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from config import VALID_CATEGORIAS_PRUEBA, VALID_CRITERIOS, VALID_RESULTADO_FINAL


class OkfEvidence(BaseModel):
    """Prueba procesal normalizada para su publicación en OKF."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    categoria: str
    subcategoria: str
    detalle: str
    objetivo_probatorio: str
    criterio_atacado: str
    source_criterion_atacado: str
    normalization_rule: str | None = None
    tipo_prueba: str
    origen: str
    aceptada: str
    peso: int = Field(ge=1, le=5)
    motivo_valoracion: str
    contradiccion_con: str

    @model_validator(mode="after")
    def validate_catalogs(self) -> Self:
        if self.categoria not in VALID_CATEGORIAS_PRUEBA:
            raise ValueError(f"categoria no canónica: {self.categoria}")
        if self.criterio_atacado not in VALID_CRITERIOS:
            raise ValueError(f"criterio no canónico: {self.criterio_atacado}")
        return self


class OkfCitation(BaseModel):
    """Cita candidata procedente del análisis estructurado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    owner_id: str
    kind: str
    source_field: str
    tema: str
    pagina: str
    analysis_quote: str

    @property
    def texto(self) -> str:
        """Alias de compatibilidad; no implica que el texto sea literal."""

        return self.analysis_quote


class OkfBurdenOfProof(BaseModel):
    """Conclusión estructurada sobre la carga de la prueba."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    quien_tenia_carga: str
    motivo: str
    cumplida: str


class OkfProvenance(BaseModel):
    """Huella reproducible de las dos fuentes que alimentan el concepto."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pdf_resource: str
    pdf_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pdf_size_bytes: int = Field(gt=0)
    pdf_page_count: int = Field(gt=0)
    analysis_source: str
    analysis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_by: str


class OkfJudgment(BaseModel):
    """Representación jurídica canónica previa al renderizado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    archivo: str
    slug: str
    title: str
    roj: str
    ecli: str
    organo: str
    fecha_resolucion: str
    es_caso_residencia_irpf: bool
    ejercicios_afectados: tuple[int, ...]
    paises: tuple[str, ...]
    pais_alegado_residencia_pf: str
    pais_cdi_aplicado: str
    se_invoca_cdi: bool
    tiebreaker_paso_decisivo: str
    criterios_detectados: tuple[str, ...]
    criterios_decisivos: tuple[str, ...]
    resumen_criterios: str
    doctrina_citada: tuple[str, ...]
    carga_prueba: OkfBurdenOfProof
    razonamiento_residencia: str
    pruebas_aeat: tuple[OkfEvidence, ...]
    pruebas_contribuyente: tuple[OkfEvidence, ...]
    resultado_final: str
    citas: tuple[OkfCitation, ...]
    confianza_extraccion: str
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_catalogs(self) -> Self:
        invalid_criteria = (set(self.criterios_detectados) | set(self.criterios_decisivos)) - (
            VALID_CRITERIOS
        )
        if invalid_criteria:
            raise ValueError(f"criterios no canónicos: {sorted(invalid_criteria)}")
        if self.resultado_final not in VALID_RESULTADO_FINAL:
            raise ValueError(f"resultado no canónico: {self.resultado_final}")
        citation_ids = tuple(citation.id for citation in self.citas)
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("las citas contienen IDs duplicados")
        return self
