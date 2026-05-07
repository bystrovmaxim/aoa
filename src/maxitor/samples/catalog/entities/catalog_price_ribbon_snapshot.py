# src/maxitor/samples/catalog/entities/catalog_price_ribbon_snapshot.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_search_boost_weight import SearchBoostWeightEntity


@entity(description="Price ribbon chained from search/boost spine (still no SKU hop)", domain=CatalogDomain)
class PriceRibbonSnapshotEntity(BaseEntity):
    id: str = Field(description="Ribbon id")
    lifecycle: CatalogDenseLifecycle = Field(description="Price ribbon lifecycle")

    search_boost: Annotated[
        AssociationOne[SearchBoostWeightEntity],
        NoInverse(),
    ] = Rel(description="Upstream search/boost facet")  # type: ignore[assignment]


PriceRibbonSnapshotEntity.model_rebuild()
