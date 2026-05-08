# src/maxitor/samples/support/entities/support_sla_interval.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.support.domain import SupportDomain
from maxitor.samples.support.entities.support_participant_row import SupportParticipantEntity
from maxitor.samples.support.entities.support_simple_lifecycle import SupportSparseLifecycle


@entity(description="SLA interval chaining from participant row", domain=SupportDomain)
class SupportSlaIntervalEntity(BaseEntity):
    id: str = Field(description="Interval id")
    lifecycle: SupportSparseLifecycle = Field(description="SLA interval lifecycle")

    ticket_human_ref: str = Field(description="Customer-visible ticket mnemonic")
    severity_score: int = Field(description="Normalized severity ordinal", ge=0)
    first_response_deadline_unix: int = Field(description="SLA first-touch deadline epoch seconds", ge=0)
    routing_queue: str = Field(description="Primary queue owning responder pool")
    language_locale: str = Field(description="Preferred conversational language tag")
    deflection_attempts: int = Field(description="Self-serve resolutions before escalation", ge=0)
    participant: Annotated[
        AssociationOne[SupportParticipantEntity],
        NoInverse(),
    ] = Rel(description="Upstream participant linkage")  # type: ignore[assignment]


SupportSlaIntervalEntity.model_rebuild()
