# src/maxitor/samples/store/entities/shipment_parcel.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Shipment parcel row", domain=StoreDomain)
class ShipmentParcelEntity(BaseEntity):
    id: str = Field(description="Parcel id")
    lifecycle: SalesOrderLifecycle = Field(description="Shipment lifecycle")
    carrier: str = Field(description="Carrier code")
    tracking_number: str = Field(description="Tracking number")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Shipped order")  # type: ignore[assignment]


ShipmentParcelEntity.model_rebuild()
