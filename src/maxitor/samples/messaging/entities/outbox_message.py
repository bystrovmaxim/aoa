# src/maxitor/samples/messaging/entities/outbox_message.py
"""Минимальная сущность для вершины домена ``messaging`` в графе."""

from pydantic import Field

from action_machine.domain import BaseEntity, entity
from maxitor.samples.messaging.domain import MessagingDomain


@entity(description="Transactional outbox row (sample)", domain=MessagingDomain)
class OutboxMessageEntity(BaseEntity):
    id: str = Field(description="Message id")
    topic: str = Field(description="Routing topic")
