# src/maxitor/samples/inventory/entities/inv_lot_age_bucket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_lot_quality_hold import LotQualityHoldEntity


@entity(description="Age stratification terminating physical operations spine", domain=InventoryDomain)
class LotAgeBucketEntity(BaseEntity):
    id: str = Field(description="Bucket id")
    lifecycle: InvDenseLifecycle = Field(description="Age bucket lifecycle")

    quality_hold: Annotated[
        AssociationOne[LotQualityHoldEntity],
        NoInverse(),
    ] = Rel(description="Upstream hold row")  # type: ignore[assignment]


LotAgeBucketEntity.model_rebuild()
