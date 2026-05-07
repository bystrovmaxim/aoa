# src/maxitor/samples/catalog/entities/catalog_search_boost_weight.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_availability_projection import AvailabilityProjectionEntity
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Search boost chaining off availability subtree", domain=CatalogDomain)
class SearchBoostWeightEntity(BaseEntity):
    id: str = Field(description="Boost id")
    lifecycle: CatalogDenseLifecycle = Field(description="Search boost lifecycle")

    availability_projection: Annotated[
        AssociationOne[AvailabilityProjectionEntity],
        NoInverse(),
    ] = Rel(description="Parent availability projection")  # type: ignore[assignment]


SearchBoostWeightEntity.model_rebuild()
