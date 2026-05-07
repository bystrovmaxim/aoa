# src/maxitor/samples/inventory/entities/inv_bin_coordinate_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvPipelineLifecycle
from maxitor.samples.inventory.entities.inv_storage_aisle_row import StorageAisleRowEntity


@entity(description="Concrete bin coordinate anchored to aisle chain", domain=InventoryDomain)
class BinCoordinateStubEntity(BaseEntity):
    lifecycle: InvPipelineLifecycle = Field(description="Bin lifecycle")
    label: str = Field(description="Coordinate label")

    aisle: Annotated[
        AssociationOne[StorageAisleRowEntity],
        NoInverse(),
    ] = Rel(description="Parent aisle")  # type: ignore[assignment]


BinCoordinateStubEntity.model_rebuild()
