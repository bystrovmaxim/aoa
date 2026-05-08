# src/maxitor/samples/inventory/entities/inv_mesh_facility_crossdock.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_crossdock_staging import CrossDockStagingEntity
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity


@entity(description="Associates upstream facility footprints with lateral cross-dock staging gates", domain=InventoryDomain)
class InvFacilityCrossdockBridgeEntity(BaseEntity):
    id: str = Field(description="Bridge id")
    lifecycle: InvDenseLifecycle = Field(description="Bridge lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Owning facility artefact")  # type: ignore[assignment]

    crossdock_gate: Annotated[
        AssociationOne[CrossDockStagingEntity],
        NoInverse(),
    ] = Rel(description="Cross-dock staging gate anchor")  # type: ignore[assignment]


InvFacilityCrossdockBridgeEntity.model_rebuild()
