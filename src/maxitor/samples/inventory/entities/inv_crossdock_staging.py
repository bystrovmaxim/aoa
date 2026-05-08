# src/maxitor/samples/inventory/entities/inv_crossdock_staging.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.entities.product_row import CatalogProductEntity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_recall_signal import RecallSignalEntity


@entity(description="Cross-dock latch following recall signalling chain", domain=InventoryDomain)
class CrossDockStagingEntity(BaseEntity):
    id: str = Field(description="Staging id")
    lifecycle: InvDenseLifecycle = Field(description="Cross-dock staging lifecycle")

    facility_tz: str = Field(description="Warehouse operational timezone identifier")
    capacity_cu_m: float = Field(description="Usable volumetric envelope cubic metres")
    hazmat_classification: str = Field(description="Material-handling tier label")
    cycle_count_due_unix: int = Field(description="Next physical audit milestone epoch seconds", ge=0)
    dock_door_anchor: str = Field(description="Primary receiving / staging door label")
    velocity_bucket: str = Field(description="ABC / throughput velocity class")
    recall_signal: Annotated[
        AssociationOne[RecallSignalEntity],
        NoInverse(),
    ] = Rel(description="Upstream recall signal")  # type: ignore[assignment]

    catalog_product_anchor: Annotated[
        AssociationOne[CatalogProductEntity],
        NoInverse(),
    ] = Rel(description="Catalog SKU keyed when diverting stock through cross-dock")  # type: ignore[assignment]

CrossDockStagingEntity.model_rebuild()
