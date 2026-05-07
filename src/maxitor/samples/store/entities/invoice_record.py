# src/maxitor/samples/store/entities/invoice_record.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Invoice row", domain=StoreDomain)
class InvoiceRecordEntity(BaseEntity):
    id: str = Field(description="Invoice id")
    lifecycle: SalesOrderLifecycle = Field(description="Invoice lifecycle")
    subtotal: float = Field(description="Subtotal", ge=0)
    total: float = Field(description="Invoice total", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Invoiced order")  # type: ignore[assignment]

    invoice_outbox_row: Annotated[
        AssociationOne["OutboxMessageEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Transactional outbox publish for invoice side-effects")  # type: ignore[assignment]


from maxitor.samples.messaging.entities.outbox_message import OutboxMessageEntity  # noqa: E402

InvoiceRecordEntity.model_rebuild()
