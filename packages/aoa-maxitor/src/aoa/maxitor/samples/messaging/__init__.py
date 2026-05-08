# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/__init__.py
"""
Notifications context: gateway, outbox entity, same end-to-end shape as ``store``.

Subpackages: ``dependencies``, ``resources``, ``plugins``, ``actions``; package-level
``_shared_notifier`` for the ``@depends`` factory (same pattern as checkout store).
"""

from aoa.maxitor.samples.messaging.domain import MessagingDomain
from aoa.maxitor.samples.messaging.entities import OutboxMessageEntity
from aoa.maxitor.samples.messaging.resources.notification_gateway import NotificationGateway

_shared_notifier = NotificationGateway(channel="shared")

__all__ = ["MessagingDomain", "NotificationGateway", "OutboxMessageEntity", "_shared_notifier"]
