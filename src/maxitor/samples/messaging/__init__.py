# src/maxitor/samples/messaging/__init__.py
"""
Контекст уведомлений: шлюз, outbox-сущность, полный контур как у ``store``.

Подмодули: ``dependencies``, ``resources``, ``plugins``, ``actions``; пакетный
``_shared_notifier`` для фабрики ``@depends`` (как в checkout store).
"""

from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities import OutboxMessageEntity
from maxitor.samples.messaging.resources.notification_gateway import NotificationGateway

_shared_notifier = NotificationGateway(channel="shared")

__all__ = ["MessagingDomain", "NotificationGateway", "OutboxMessageEntity", "_shared_notifier"]
