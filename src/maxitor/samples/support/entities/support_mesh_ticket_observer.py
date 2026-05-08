# src/maxitor/samples/support/entities/support_mesh_ticket_observer.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.support.domain import SupportDomain
from maxitor.samples.support.entities.support_participant_row import SupportParticipantEntity
from maxitor.samples.support.entities.support_simple_lifecycle import SupportSparseLifecycle
from maxitor.samples.support.entities.support_ticket_aggregate import SupportTicketAggregateEntity


@entity(description="Associative pairing on sparse support graph (triangle completion on ticket spine)", domain=SupportDomain)
class SupportTicketParticipantPairEntity(BaseEntity):
    id: str = Field(description="Assoc id")
    lifecycle: SupportSparseLifecycle = Field(description="Pair lifecycle")

    ticket_human_ref: str = Field(description="Customer-visible ticket mnemonic")
    severity_score: int = Field(description="Normalized severity ordinal", ge=0)
    first_response_deadline_unix: int = Field(description="SLA first-touch deadline epoch seconds", ge=0)
    routing_queue: str = Field(description="Primary queue owning responder pool")
    language_locale: str = Field(description="Preferred conversational language tag")
    deflection_attempts: int = Field(description="Self-serve resolutions before escalation", ge=0)
    ticket: Annotated[
        AssociationOne[SupportTicketAggregateEntity],
        NoInverse(),
    ] = Rel(description="Ticket aggregate anchor")  # type: ignore[assignment]

    participant: Annotated[
        AssociationOne[SupportParticipantEntity],
        NoInverse(),
    ] = Rel(description="Participant row anchor")  # type: ignore[assignment]


SupportTicketParticipantPairEntity.model_rebuild()
