# src/maxitor/samples/catalog/entities/catalog_shelf_placement_hint.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Planogram spine root — no SKU foreign key (merchant-only subtree)", domain=CatalogDomain)
class ShelfPlacementHintEntity(BaseEntity):
    lifecycle: CatalogDenseLifecycle = Field(description="Shelf placement lifecycle")
    id: str = Field(description="Hint id")


ShelfPlacementHintEntity.model_rebuild()
