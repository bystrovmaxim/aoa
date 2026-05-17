# packages/aoa-examples/src/aoa/examples/model/store/entities/invoice_record.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.messaging.entities.outbox_message import OutboxMessageEntity
from aoa.examples.model.store.entities.sales_core import SalesOrderEntity
from aoa.examples.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.examples.model.store.store_domain import StoreDomain


@entity(description="Invoice row", domain=StoreDomain)
class InvoiceRecordEntity(BaseEntity):
    id: str = Field(description="Invoice id")
    lifecycle: SalesOrderLifecycle = Field(description="Invoice lifecycle")
    subtotal: float = Field(description="Subtotal", ge=0)
    total: float = Field(description="Invoice total", ge=0)

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Invoiced order")  # type: ignore[assignment]

    invoice_outbox_row: Annotated[
        AssociationOne[OutboxMessageEntity],
        NoInverse(),
    ] = Rel(description="Transactional outbox publish for invoice side-effects")  # type: ignore[assignment]

InvoiceRecordEntity.model_rebuild()
