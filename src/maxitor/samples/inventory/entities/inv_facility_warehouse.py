# src/maxitor/samples/inventory/entities/inv_facility_warehouse.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvPipelineLifecycle


@entity(description="Warehouse / facility hub for inventory locations and cross-dock operations", domain=InventoryDomain)
class FacilityWarehouseEntity(BaseEntity):
    id: str = Field(description="Facility id")
    lifecycle: InvPipelineLifecycle = Field(description="Facility lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")


FacilityWarehouseEntity.model_rebuild()
