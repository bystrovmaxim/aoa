# src/maxitor/samples/support/entities/support_comment_thread_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.support.domain import SupportDomain
from maxitor.samples.support.entities.support_simple_lifecycle import SupportSparseLifecycle
from maxitor.samples.support.entities.support_sla_interval import SupportSlaIntervalEntity


@entity(description="Conversation stub tail on SLA segment (no fan-in back to ticket hub)", domain=SupportDomain)
class SupportCommentThreadStubEntity(BaseEntity):
    id: str = Field(description="Thread stub id")
    lifecycle: SupportSparseLifecycle = Field(description="Thread lifecycle")

    sla_interval: Annotated[
        AssociationOne[SupportSlaIntervalEntity],
        NoInverse(),
    ] = Rel(description="Parent SLA interval artefact")  # type: ignore[assignment]


SupportCommentThreadStubEntity.model_rebuild()
