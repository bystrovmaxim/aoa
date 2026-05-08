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
    id: str = Field(description="Aisle id")
    lifecycle: InvPipelineLifecycle = Field(description="Aisle lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Parent facility warehouse")  # type: ignore[assignment]


StorageAisleRowEntity.model_rebuild()
