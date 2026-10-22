# packages/aoa-demo/src/aoa/demo/model/support/entities/support_mesh_ticket_observer.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.support.entities.support_participant_row import SupportParticipantCoreEntity
from aoa.demo.model.support.entities.support_simple_lifecycle import SupportSparseLifecycle
from aoa.demo.model.support.entities.support_ticket_aggregate import SupportTicketAggregateCoreEntity
from aoa.demo.model.support.support_domain import SupportDomain


@entity(
    description="Associative pairing on sparse support graph (triangle completion on ticket spine)",
    domain=SupportDomain,
)
class SupportTicketParticipantPairCoreEntity(BaseCoreEntity):
    id: str = Field(description="Assoc id")
    lifecycle: SupportSparseLifecycle = Field(description="Pair lifecycle")

    ticket_human_ref: str = Field(description="Customer-visible ticket mnemonic")
    severity_score: int = Field(description="Normalized severity ordinal", ge=0)
    first_response_deadline_unix: int = Field(description="SLA first-touch deadline epoch seconds", ge=0)
    routing_queue: str = Field(description="Primary queue owning responder pool")
    language_locale: str = Field(description="Preferred conversational language tag")
    deflection_attempts: int = Field(description="Self-serve resolutions before escalation", ge=0)
    ticket: Annotated[
        AssociationOne[SupportTicketAggregateCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Ticket aggregate anchor"
    )  # type: ignore[assignment]

    participant: Annotated[
        AssociationOne[SupportParticipantCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Participant row anchor"
    )  # type: ignore[assignment]


SupportTicketParticipantPairCoreEntity.model_rebuild()
