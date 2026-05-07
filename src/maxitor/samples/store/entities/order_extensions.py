# src/maxitor/samples/store/entities/order_extensions.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle, SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity, SalesOrderLineEntity


@entity(description="Payment authorization row", domain=StoreDomain)
class PaymentAuthorizationEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Authorization lifecycle")
    id: str = Field(description="Authorization id")
    provider: str = Field(description="PSP name")
    approved_amount: float = Field(description="Approved amount", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Authorized order")  # type: ignore[assignment]


@entity(description="Payment capture row", domain=StoreDomain)
class PaymentCaptureEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Capture lifecycle")
    id: str = Field(description="Capture id")
    amount: float = Field(description="Captured amount", ge=0)
    captured_at: str = Field(description="Capture timestamp")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Captured order")  # type: ignore[assignment]


@entity(description="Refund request row", domain=StoreDomain)
class RefundRequestEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Refund lifecycle")
    id: str = Field(description="Refund id")
    amount: float = Field(description="Requested refund amount", ge=0)
    reason: str = Field(description="Refund reason")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Refunded order")  # type: ignore[assignment]


@entity(description="Shipment parcel row", domain=StoreDomain)
class ShipmentParcelEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Shipment lifecycle")
    id: str = Field(description="Parcel id")
    carrier: str = Field(description="Carrier code")
    tracking_number: str = Field(description="Tracking number")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Shipped order")  # type: ignore[assignment]


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


@entity(description="Invoice row", domain=StoreDomain)
class InvoiceRecordEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Invoice lifecycle")
    id: str = Field(description="Invoice id")
    subtotal: float = Field(description="Subtotal", ge=0)
    total: float = Field(description="Invoice total", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Invoiced order")  # type: ignore[assignment]


@entity(description="Tax line row", domain=StoreDomain)
class TaxLineEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Tax line lifecycle")
    id: str = Field(description="Tax line id")
    tax_code: str = Field(description="Tax code")
    tax_amount: float = Field(description="Tax amount", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Taxed order")  # type: ignore[assignment]


@entity(description="Discount application row", domain=StoreDomain)
class DiscountApplicationEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Discount lifecycle")
    id: str = Field(description="Discount application id")
    coupon_code: str = Field(description="Coupon code")
    discount_amount: float = Field(description="Discount amount", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Discounted order")  # type: ignore[assignment]


@entity(description="Fulfillment task row", domain=StoreDomain)
class FulfillmentTaskEntity(BaseEntity):
    lifecycle: SalesOrderLineLifecycle = Field(description="Fulfillment task lifecycle")
    id: str = Field(description="Task id")
    assignee: str = Field(description="Assigned worker")
    task_kind: str = Field(description="Task kind")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Target order line")  # type: ignore[assignment]


@entity(description="Return request row", domain=StoreDomain)
class ReturnRequestEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Return lifecycle")
    id: str = Field(description="Return request id")
    reason: str = Field(description="Return reason")
    status: str = Field(description="Return status")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Returned order")  # type: ignore[assignment]


PaymentAuthorizationEntity.model_rebuild()
PaymentCaptureEntity.model_rebuild()
RefundRequestEntity.model_rebuild()
ShipmentParcelEntity.model_rebuild()
ShipmentTrackingEventEntity.model_rebuild()
InvoiceRecordEntity.model_rebuild()
TaxLineEntity.model_rebuild()
DiscountApplicationEntity.model_rebuild()
FulfillmentTaskEntity.model_rebuild()
ReturnRequestEntity.model_rebuild()
