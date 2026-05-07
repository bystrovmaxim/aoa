# src/maxitor/samples/inventory/entities/inv_mesh_bin_age.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_bin_coordinate_stub import BinCoordinateStubEntity
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_lot_age_bucket import LotAgeBucketEntity


@entity(description="Correlates physical bin coordinates with terminal aging buckets (facility mesh)", domain=InventoryDomain)
class InvBinAgeCorrelateEntity(BaseEntity):
    lifecycle: InvDenseLifecycle = Field(description="Correlator lifecycle")
    id: str = Field(description="Correlator id")

    bin_coordinate: Annotated[
        AssociationOne[BinCoordinateStubEntity],
        NoInverse(),
    ] = Rel(description="Structural bin anchor")  # type: ignore[assignment]

    age_bucket: Annotated[
        AssociationOne[LotAgeBucketEntity],
        NoInverse(),
    ] = Rel(description="Operational aging artefact anchor")  # type: ignore[assignment]


InvBinAgeCorrelateEntity.model_rebuild()
