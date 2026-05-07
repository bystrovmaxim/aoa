# src/maxitor/samples/inventory/entities/inv_lot_snapshot_ledger.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_bin_coordinate_stub import BinCoordinateStubEntity
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity


@entity(description="Snapshot ledger marrying facility head with bin spine (dual anchor, non-radial)", domain=InventoryDomain)
class LotSnapshotLedgerEntity(BaseEntity):
    lifecycle: InvDenseLifecycle = Field(description="Snapshot ledger lifecycle")
    id: str = Field(description="Ledger id")

    facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Facility lineage anchor")  # type: ignore[assignment]

    bin_coordinate: Annotated[
        AssociationOne[BinCoordinateStubEntity],
        NoInverse(),
    ] = Rel(description="Bin coordinate lineage anchor")  # type: ignore[assignment]


LotSnapshotLedgerEntity.model_rebuild()
