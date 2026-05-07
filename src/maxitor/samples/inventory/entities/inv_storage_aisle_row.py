# src/maxitor/samples/inventory/entities/inv_storage_aisle_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvPipelineLifecycle
from maxitor.samples.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity


@entity(description="Storage aisle row inside a warehouse facility", domain=InventoryDomain)
class StorageAisleRowEntity(BaseEntity):
    lifecycle: InvPipelineLifecycle = Field(description="Aisle lifecycle")
    id: str = Field(description="Aisle id")

    facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Parent facility warehouse")  # type: ignore[assignment]


StorageAisleRowEntity.model_rebuild()
