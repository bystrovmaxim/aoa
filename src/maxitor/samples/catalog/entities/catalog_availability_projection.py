# src/maxitor/samples/catalog/entities/catalog_availability_projection.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Availability projection subgraph root independent of SKU FK", domain=CatalogDomain)
class AvailabilityProjectionEntity(BaseEntity):
    id: str = Field(description="Projection id")
    lifecycle: CatalogDenseLifecycle = Field(description="Availability projection lifecycle")


AvailabilityProjectionEntity.model_rebuild()
