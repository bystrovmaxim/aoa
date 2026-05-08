# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/shipment_parcel.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Shipment parcel row", domain=StoreDomain)
class ShipmentParcelEntity(BaseEntity):
    id: str = Field(description="Parcel id")
    lifecycle: SalesOrderLifecycle = Field(description="Shipment lifecycle")
    carrier: str = Field(description="Carrier code")
    tracking_number: str = Field(description="Tracking number")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Shipped order")  # type: ignore[assignment]

    origin_facility: Annotated[
        AssociationOne[FacilityWarehouseEntity],
        NoInverse(),
    ] = Rel(description="Inventory facility staging this shipment")  # type: ignore[assignment]

ShipmentParcelEntity.model_rebuild()
