# src/maxitor/samples/inventory/entities/inv_bin_coordinate_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvPipelineLifecycle
from maxitor.samples.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity
from maxitor.samples.inventory.entities.inv_storage_aisle_row import StorageAisleRowEntity


@entity(description="Concrete bin coordinate anchored to aisle and facility", domain=InventoryDomain)
class BinCoordinateStubEntity(BaseEntity):
    id: str = Field(description="Bin coordinate id")
    lifecycle: InvPipelineLifecycle = Field(description="Bin lifecycle")
    label: str = Field(description="Coordinate label")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    aisle: Annotated[
        AssociationOne[StorageAisleRowEntity],
        NoInverse(),
    ] = Rel(description="Parent aisle")  # type: ignore[assignment]

    facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Owning warehouse facility")  # type: ignore[assignment]


BinCoordinateStubEntity.model_rebuild()
