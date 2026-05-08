# packages/aoa-maxitor/src/aoa/maxitor/samples/support/entities/support_ticket_aggregate.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderEntity
from aoa.maxitor.samples.support.domain import SupportDomain
from aoa.maxitor.samples.support.entities.support_simple_lifecycle import SupportSparseLifecycle


@entity(description="Sparse support-domain hub (minimal star topology)", domain=SupportDomain)
class SupportTicketAggregateEntity(BaseEntity):
    id: str = Field(description="Ticket id")
    lifecycle: SupportSparseLifecycle = Field(description="Ticket lifecycle")

    ticket_human_ref: str = Field(description="Customer-visible ticket mnemonic")
    severity_score: int = Field(description="Normalized severity ordinal", ge=0)
    first_response_deadline_unix: int = Field(description="SLA first-touch deadline epoch seconds", ge=0)
    routing_queue: str = Field(description="Primary queue owning responder pool")
    language_locale: str = Field(description="Preferred conversational language tag")
    deflection_attempts: int = Field(description="Self-serve resolutions before escalation", ge=0)
    related_commerce_order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Linked storefront sales order motivating the ticket")  # type: ignore[assignment]

SupportTicketAggregateEntity.model_rebuild()
