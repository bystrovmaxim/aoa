# src/maxitor/samples/support/entities/support_participant_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.support.domain import SupportDomain
from maxitor.samples.support.entities.support_simple_lifecycle import SupportSparseLifecycle
from maxitor.samples.support.entities.support_ticket_aggregate import SupportTicketAggregateEntity


@entity(description="Ticket participant row (linear chain head off ticket)", domain=SupportDomain)
class SupportParticipantEntity(BaseEntity):
    id: str = Field(description="Participant row id")
    lifecycle: SupportSparseLifecycle = Field(description="Participant lifecycle")

    ticket: Annotated[
        AssociationOne[SupportTicketAggregateEntity],
        NoInverse(),
    ] = Rel(description="Parent ticket aggregate")  # type: ignore[assignment]


SupportParticipantEntity.model_rebuild()
