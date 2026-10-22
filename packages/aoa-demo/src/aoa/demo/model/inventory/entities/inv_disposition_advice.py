# packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_disposition_advice.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.inventory.domain import InventoryDomain
from aoa.demo.model.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from aoa.demo.model.inventory.entities.inv_facility_warehouse import FacilityWarehouseCoreEntity
from aoa.demo.model.inventory.entities.inv_lot_freeze_flag import LotFreezeFlagCoreEntity


@entity(description="Disposition advice for a frozen lot within a facility", domain=InventoryDomain)
class DispositionAdviceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Advice id")
    lifecycle: InvDenseLifecycle = Field(description="Disposition lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    freeze_flag: Annotated[
        AssociationOne[LotFreezeFlagCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Upstream freeze flag"
    )  # type: ignore[assignment]

    facility: Annotated[
        AssociationOne[FacilityWarehouseCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Facility execution context"
    )  # type: ignore[assignment]


DispositionAdviceCoreEntity.model_rebuild()
