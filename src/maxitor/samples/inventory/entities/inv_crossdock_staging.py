# src/maxitor/samples/inventory/entities/inv_crossdock_staging.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_recall_signal import RecallSignalEntity


@entity(description="Cross-dock latch following recall signalling chain", domain=InventoryDomain)
class CrossDockStagingEntity(BaseEntity):
    lifecycle: InvDenseLifecycle = Field(description="Cross-dock staging lifecycle")
    id: str = Field(description="Staging id")

    recall_signal: Annotated[
        AssociationOne[RecallSignalEntity],
        NoInverse(),
    ] = Rel(description="Upstream recall signal")  # type: ignore[assignment]


CrossDockStagingEntity.model_rebuild()
