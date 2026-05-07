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
    lifecycle: SupportSparseLifecycle = Field(description="SLA interval lifecycle")
    id: str = Field(description="Interval id")

    participant: Annotated[
        AssociationOne[SupportParticipantEntity],
        NoInverse(),
    ] = Rel(description="Upstream participant linkage")  # type: ignore[assignment]


SupportSlaIntervalEntity.model_rebuild()
