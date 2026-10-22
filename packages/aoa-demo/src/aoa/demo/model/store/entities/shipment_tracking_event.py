# packages/aoa-demo/src/aoa/demo/model/store/entities/shipment_tracking_event.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.demo.model.store.entities.shipment_parcel import ShipmentParcelCoreEntity
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Shipment tracking event row", domain=StoreDomain)
class ShipmentTrackingEventCoreEntity(BaseCoreEntity):
    id: str = Field(description="Tracking event id")
    lifecycle: SalesOrderLifecycle = Field(description="Tracking event lifecycle")
    status: str = Field(description="Carrier status")
    location: str = Field(description="Carrier location")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    parcel: Annotated[
        AssociationOne[ShipmentParcelCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Owner parcel"
    )  # type: ignore[assignment]


ShipmentTrackingEventCoreEntity.model_rebuild()
