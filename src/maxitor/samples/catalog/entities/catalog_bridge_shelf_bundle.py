# src/maxitor/samples/catalog/entities/catalog_bridge_shelf_bundle.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_bundle_cardinality_rule import BundleCardinalityRuleEntity
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintEntity


@entity(description="Associative row sewing planogram island to bundle cardinality island", domain=CatalogDomain)
class CatalogShelfBundleLinkEntity(BaseEntity):
    id: str = Field(description="Assoc id")
    lifecycle: CatalogDenseLifecycle = Field(description="Link lifecycle")

    shelf_hint: Annotated[
        AssociationOne[ShelfPlacementHintEntity],
        NoInverse(),
    ] = Rel(description="Planogram spine anchor")  # type: ignore[assignment]

    bundle_rule: Annotated[
        AssociationOne[BundleCardinalityRuleEntity],
        NoInverse(),
    ] = Rel(description="Bundle cardinality anchor")  # type: ignore[assignment]


CatalogShelfBundleLinkEntity.model_rebuild()
