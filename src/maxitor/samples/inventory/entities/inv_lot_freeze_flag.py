# src/maxitor/samples/inventory/entities/inv_lot_freeze_flag.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_bin_coordinate_stub import BinCoordinateStubEntity
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity


@entity(description="Lot freeze flag anchored to bin and facility", domain=InventoryDomain)
class LotFreezeFlagEntity(BaseEntity):
    id: str = Field(description="Flag id")
    lifecycle: InvDenseLifecycle = Field(description="Freeze flag lifecycle")

    bin_coordinate: Annotated[
        AssociationOne[BinCoordinateStubEntity],
        NoInverse(),
    ] = Rel(description="Owning bin coordinate")  # type: ignore[assignment]

    facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Facility where the frozen lot is held")  # type: ignore[assignment]


LotFreezeFlagEntity.model_rebuild()
