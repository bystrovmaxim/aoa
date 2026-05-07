# src/maxitor/samples/inventory/entities/inv_lot_freeze_flag.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_bin_coordinate_stub import BinCoordinateStubEntity
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle


@entity(description="Freeze flag anchored to physical bin spine (no abstract aggregate FK)", domain=InventoryDomain)
class LotFreezeFlagEntity(BaseEntity):
    lifecycle: InvDenseLifecycle = Field(description="Freeze flag lifecycle")
    id: str = Field(description="Flag id")

    bin_coordinate: Annotated[
        AssociationOne[BinCoordinateStubEntity],
        NoInverse(),
    ] = Rel(description="Owning bin coordinate")  # type: ignore[assignment]


LotFreezeFlagEntity.model_rebuild()
