# src/maxitor/samples/store/entities/store_order_shipment_estimate.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.shipment_parcel import ShipmentParcelEntity


@entity(description="Shipment ETA heuristic hanging off parcels instead of repeating order centroid", domain=StoreDomain)
class ShipmentEstimateEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Estimate lifecycle")
    id: str = Field(description="Estimate id")

    parcel: Annotated[
        AssociationOne[ShipmentParcelEntity],
        NoInverse(),
    ] = Rel(description="Parent parcel artefact")  # type: ignore[assignment]


ShipmentEstimateEntity.model_rebuild()
