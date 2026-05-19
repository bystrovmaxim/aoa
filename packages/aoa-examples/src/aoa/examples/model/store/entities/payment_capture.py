# packages/aoa-examples/src/aoa/examples/model/store/entities/payment_capture.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.messaging.entities.msg_webhook_ingress_receipt import WebhookIngressReceiptEntity
from aoa.examples.model.store.entities.sales_core import SalesOrderEntity
from aoa.examples.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.examples.model.store.store_domain import StoreDomain


@entity(description="Payment capture row", domain=StoreDomain)
class PaymentCaptureEntity(BaseEntity):
    id: str = Field(description="Capture id")
    lifecycle: SalesOrderLifecycle = Field(description="Capture lifecycle")
    amount: float = Field(description="Captured amount", ge=0)
    captured_at: str = Field(description="Capture timestamp")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Captured order")  # type: ignore[assignment]

    processor_webhook_receipt: Annotated[
        AssociationOne[WebhookIngressReceiptEntity],
        NoInverse(),
    ] = Rel(description="Ingress receipt for PSP / acquirer callback correlation")  # type: ignore[assignment]

PaymentCaptureEntity.model_rebuild()
