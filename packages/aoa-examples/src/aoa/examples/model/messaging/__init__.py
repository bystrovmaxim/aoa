# packages/aoa-examples/src/aoa/examples/model/messaging/__init__.py
"""
Notifications context: gateway, outbox entity, same end-to-end shape as ``store``.

Subpackages: ``dependencies``, ``resources``, ``plugins``, ``actions``; package-level
``_shared_notifier`` for the ``@depends`` factory (same pattern as checkout store).
"""

from aoa.examples.model.messaging.domain import MessagingDomain
from aoa.examples.model.messaging.entities import OutboxMessageEntity
from aoa.examples.model.messaging.resources.notification_gateway import NotificationGateway

_shared_notifier = NotificationGateway(channel="shared")

__all__ = ["MessagingDomain", "NotificationGateway", "OutboxMessageEntity", "_shared_notifier"]
