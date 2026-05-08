# packages/aoa-maxitor/src/aoa/maxitor/samples/store/dependencies/__init__.py
"""Wires the store to billing and messaging (like a real service)."""

from aoa.maxitor.samples.billing import PaymentGateway
from aoa.maxitor.samples.messaging import NotificationGateway, _shared_notifier

__all__ = ["NotificationGateway", "PaymentGateway", "_shared_notifier"]
