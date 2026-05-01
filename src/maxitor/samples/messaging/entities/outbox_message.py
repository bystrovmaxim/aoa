# src/maxitor/samples/messaging/entities/outbox_message.py
"""Минимальная сущность для вершины домена ``messaging`` в графе."""

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.outbox_lifecycle import OutboxMessageLifecycle


@entity(description="Transactional outbox row (sample)", domain=MessagingDomain)
class OutboxMessageEntity(BaseEntity):
    lifecycle: OutboxMessageLifecycle = Field(description="Outbox message lifecycle")
    id: str = Field(description="Message id")
    topic: str = Field(description="Routing topic")
