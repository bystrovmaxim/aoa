# src/maxitor/samples/support/entities/support_ticket_aggregate.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.support.domain import SupportDomain
from maxitor.samples.support.entities.support_simple_lifecycle import SupportSparseLifecycle


@entity(description="Sparse support-domain hub (minimal star topology)", domain=SupportDomain)
class SupportTicketAggregateEntity(BaseEntity):
    id: str = Field(description="Ticket id")
    lifecycle: SupportSparseLifecycle = Field(description="Ticket lifecycle")

    related_commerce_order: Annotated[
        AssociationOne["SalesOrderEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Linked storefront sales order motivating the ticket")  # type: ignore[assignment]


from maxitor.samples.store.entities.sales_core import SalesOrderEntity  # noqa: E402

SupportTicketAggregateEntity.model_rebuild()
