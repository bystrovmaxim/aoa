# src/maxitor/samples/inventory/entities/inv_facility_warehouse.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvPipelineLifecycle


@entity(description="Warehouse / facility hub for inventory locations and cross-dock operations", domain=InventoryDomain)
class FacilityWarehouseEntity(BaseEntity):
    lifecycle: InvPipelineLifecycle = Field(description="Facility lifecycle")
    id: str = Field(description="Facility id")


FacilityWarehouseEntity.model_rebuild()
