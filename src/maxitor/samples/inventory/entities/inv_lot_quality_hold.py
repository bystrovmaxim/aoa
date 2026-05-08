# src/maxitor/samples/inventory/entities/inv_lot_quality_hold.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_crossdock_staging import CrossDockStagingEntity
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle


@entity(description="Quality hold chaining off cross-dock staging", domain=InventoryDomain)
class LotQualityHoldEntity(BaseEntity):
    id: str = Field(description="Hold id")
    lifecycle: InvDenseLifecycle = Field(description="Quality hold lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    crossdock: Annotated[
        AssociationOne[CrossDockStagingEntity],
        NoInverse(),
    ] = Rel(description="Parent staging row")  # type: ignore[assignment]


LotQualityHoldEntity.model_rebuild()
