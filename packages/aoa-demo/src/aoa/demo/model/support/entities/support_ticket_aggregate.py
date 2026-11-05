# packages/aoa-demo/src/aoa/demo/model/support/entities/support_ticket_aggregate.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.support.entities.support_simple_lifecycle import SupportSparseLifecycle
from aoa.demo.model.support.resources.storage import SupportStorage


@entity(description="Sparse support-domain hub (minimal star topology)", resource=SupportStorage)
class SupportTicketAggregateCoreEntity(BaseCoreEntity):
    id: str = Field(description="Ticket id")
    lifecycle: SupportSparseLifecycle = Field(description="Ticket lifecycle")

    ticket_human_ref: str = Field(description="Customer-visible ticket mnemonic")
    severity_score: int = Field(description="Normalized severity ordinal", ge=0)
    first_response_deadline_unix: int = Field(description="SLA first-touch deadline epoch seconds", ge=0)
    routing_queue: str = Field(description="Primary queue owning responder pool")
    language_locale: str = Field(description="Preferred conversational language tag")
    deflection_attempts: int = Field(description="Self-serve resolutions before escalation", ge=0)


SupportTicketAggregateCoreEntity.model_rebuild()
