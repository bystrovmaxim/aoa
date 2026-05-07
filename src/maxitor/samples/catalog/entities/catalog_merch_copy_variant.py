# src/maxitor/samples/catalog/entities/catalog_merch_copy_variant.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintEntity


@entity(description="Merch copy chained from planogram hint spine", domain=CatalogDomain)
class MerchCopyVariantEntity(BaseEntity):
    lifecycle: CatalogDenseLifecycle = Field(description="Merch copy lifecycle")
    id: str = Field(description="Variant id")

    shelf_hint: Annotated[
        AssociationOne[ShelfPlacementHintEntity],
        NoInverse(),
    ] = Rel(description="Owning shelf placement artefact")  # type: ignore[assignment]


MerchCopyVariantEntity.model_rebuild()
