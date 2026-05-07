# src/maxitor/samples/support/entities/support_ticket_aggregate.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.support.domain import SupportDomain
from maxitor.samples.support.entities.support_simple_lifecycle import SupportSparseLifecycle


@entity(description="Sparse support-domain hub (minimal star topology)", domain=SupportDomain)
class SupportTicketAggregateEntity(BaseEntity):
    lifecycle: SupportSparseLifecycle = Field(description="Ticket lifecycle")
    id: str = Field(description="Ticket id")


SupportTicketAggregateEntity.model_rebuild()
