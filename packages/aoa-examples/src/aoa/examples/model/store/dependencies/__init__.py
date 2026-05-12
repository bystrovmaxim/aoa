# packages/aoa-examples/src/aoa/examples/model/store/dependencies/__init__.py
"""Wires the store to billing and messaging (like a real service)."""

from aoa.examples.model.billing import PaymentGateway
from aoa.examples.model.messaging import NotificationGateway, _shared_notifier

__all__ = ["NotificationGateway", "PaymentGateway", "_shared_notifier"]
