# packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_crossdock_staging.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from aoa.demo.model.inventory.entities.inv_recall_signal import RecallSignalCoreEntity
from aoa.demo.model.inventory.resources.storage import InventoryStorage


@entity(description="Cross-dock latch following recall signalling chain", resource=InventoryStorage)
class CrossDockStagingCoreEntity(BaseCoreEntity):
    id: str = Field(description="Staging id")
    lifecycle: InvDenseLifecycle = Field(description="Cross-dock staging lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    recall_signal: Annotated[
        AssociationOne[RecallSignalCoreEntity],
        NoInverse(),
    ] = Field(
        description="Upstream recall signal"
    )



CrossDockStagingCoreEntity.model_rebuild()
