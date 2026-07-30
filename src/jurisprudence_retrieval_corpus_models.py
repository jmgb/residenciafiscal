"""Contrato del corpus agregado de recuperación jurisprudencial."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from jurisprudence_case_catalogs import (
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)
from jurisprudence_case_retrieval_models import RetrievalUnit


class RetrievalCorpusSource(JurisprudenceCaseModel):
    judgment_id: Identifier
    index_resource: NonEmptyText
    index_sha256: Sha256


class RetrievalCorpus(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-retrieval-corpus/1"]
    sample_id: Identifier
    sources: Annotated[tuple[RetrievalCorpusSource, ...], Field(min_length=1)]
    units: Annotated[tuple[RetrievalUnit, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_relationships(self) -> Self:
        source_ids = tuple(item.judgment_id for item in self.sources)
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("sources contiene sentencias duplicadas")
        unit_ids = tuple(item.unit_id for item in self.units)
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("units contiene identificadores duplicados")
        unknown = {item.judgment_id for item in self.units} - set(source_ids)
        if unknown:
            raise ValueError(f"units referencia sentencias desconocidas: {sorted(unknown)}")
        return self
