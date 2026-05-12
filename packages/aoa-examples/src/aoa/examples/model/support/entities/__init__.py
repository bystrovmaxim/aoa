# packages/aoa-examples/src/aoa/examples/model/support/entities/__init__.py
from __future__ import annotations

from aoa.examples.model.support.entities.support_comment_thread_stub import SupportCommentThreadStubEntity
from aoa.examples.model.support.entities.support_mesh_ticket_observer import SupportTicketParticipantPairEntity
from aoa.examples.model.support.entities.support_participant_row import SupportParticipantEntity
from aoa.examples.model.support.entities.support_simple_lifecycle import SupportSparseLifecycle
from aoa.examples.model.support.entities.support_sla_interval import SupportSlaIntervalEntity
from aoa.examples.model.support.entities.support_ticket_aggregate import SupportTicketAggregateEntity

__all__ = [
    "SupportCommentThreadStubEntity",
    "SupportParticipantEntity",
    "SupportSlaIntervalEntity",
    "SupportSparseLifecycle",
    "SupportTicketAggregateEntity",
    "SupportTicketParticipantPairEntity",
]
