# src/maxitor/samples/store/entities/shipment_tracking_event.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.shipment_parcel import ShipmentParcelEntity


@entity(description="Shipment tracking event row", domain=StoreDomain)
class ShipmentTrackingEventEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Tracking event lifecycle")
    id: str = Field(description="Tracking event id")
    status: str = Field(description="Carrier status")
    location: str = Field(description="Carrier location")

    parcel: Annotated[
        AssociationOne[ShipmentParcelEntity],
        NoInverse(),
    ] = Rel(description="Owner parcel")  # type: ignore[assignment]


ShipmentTrackingEventEntity.model_rebuild()
