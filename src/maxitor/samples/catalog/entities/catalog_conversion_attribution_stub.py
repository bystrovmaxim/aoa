# src/maxitor/samples/catalog/entities/catalog_conversion_attribution_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_touch_moment import TouchMomentEntity


@entity(description="Conversion attribution stub chained from touch moment", domain=CatalogDomain)
class ConversionAttributionStubEntity(BaseEntity):
    id: str = Field(description="Stub id")
    lifecycle: CatalogDenseLifecycle = Field(description="Conversion stub lifecycle")

    touch: Annotated[
        AssociationOne[TouchMomentEntity],
        NoInverse(),
    ] = Rel(description="Last touch linkage")  # type: ignore[assignment]


ConversionAttributionStubEntity.model_rebuild()
