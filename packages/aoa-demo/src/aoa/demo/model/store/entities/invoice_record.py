# packages/aoa-demo/src/aoa/demo/model/store/entities/invoice_record.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.messaging.entities.outbox_message import OutboxMessageCoreEntity
from aoa.demo.model.store.entities.sales_core import SalesOrderCoreEntity
from aoa.demo.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Invoice row", domain=StoreDomain)
class InvoiceRecordCoreEntity(BaseCoreEntity):
    id: str = Field(description="Invoice id")
    lifecycle: SalesOrderLifecycle = Field(description="Invoice lifecycle")
    subtotal: float = Field(description="Subtotal", ge=0)
    total: float = Field(description="Invoice total", ge=0)

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Invoiced order"
    )  # type: ignore[assignment]

    invoice_outbox_row: Annotated[
        AssociationOne[OutboxMessageCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Transactional outbox publish for invoice side-effects"
    )  # type: ignore[assignment]


InvoiceRecordCoreEntity.model_rebuild()
