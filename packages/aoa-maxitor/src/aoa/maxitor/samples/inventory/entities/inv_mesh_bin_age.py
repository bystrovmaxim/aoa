# packages/aoa-maxitor/src/aoa/maxitor/samples/inventory/entities/inv_mesh_bin_age.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.inventory.domain import InventoryDomain
from aoa.maxitor.samples.inventory.entities.inv_bin_coordinate_stub import BinCoordinateStubEntity
from aoa.maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from aoa.maxitor.samples.inventory.entities.inv_lot_age_bucket import LotAgeBucketEntity


@entity(description="Correlates physical bin coordinates with terminal aging buckets (facility mesh)", domain=InventoryDomain)
class InvBinAgeCorrelateEntity(BaseEntity):
    id: str = Field(description="Correlator id")
    lifecycle: InvDenseLifecycle = Field(description="Correlator lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    bin_coordinate: Annotated[
        AssociationOne[BinCoordinateStubEntity],
        NoInverse(),
    ] = Rel(description="Structural bin anchor")  # type: ignore[assignment]

    age_bucket: Annotated[
        AssociationOne[LotAgeBucketEntity],
        NoInverse(),
    ] = Rel(description="Operational aging artefact anchor")  # type: ignore[assignment]


InvBinAgeCorrelateEntity.model_rebuild()
