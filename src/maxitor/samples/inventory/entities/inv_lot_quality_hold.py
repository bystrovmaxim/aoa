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
    lifecycle: InvDenseLifecycle = Field(description="Quality hold lifecycle")
    id: str = Field(description="Hold id")

    crossdock: Annotated[
        AssociationOne[CrossDockStagingEntity],
        NoInverse(),
    ] = Rel(description="Parent staging row")  # type: ignore[assignment]


LotQualityHoldEntity.model_rebuild()
