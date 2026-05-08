# packages/aoa-maxitor/src/aoa/maxitor/samples/inventory/entities/inv_disposition_advice.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.inventory.domain import InventoryDomain
from aoa.maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from aoa.maxitor.samples.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity
from aoa.maxitor.samples.inventory.entities.inv_lot_freeze_flag import LotFreezeFlagEntity


@entity(description="Disposition advice for a frozen lot within a facility", domain=InventoryDomain)
class DispositionAdviceEntity(BaseEntity):
    id: str = Field(description="Advice id")
    lifecycle: InvDenseLifecycle = Field(description="Disposition lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    freeze_flag: Annotated[
        AssociationOne[LotFreezeFlagEntity],
        NoInverse(),
    ] = Rel(description="Upstream freeze flag")  # type: ignore[assignment]

    facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Facility execution context")  # type: ignore[assignment]


DispositionAdviceEntity.model_rebuild()
