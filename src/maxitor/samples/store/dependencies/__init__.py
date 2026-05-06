# src/maxitor/samples/store/dependencies/__init__.py
"""Wires the store to billing and messaging (like a real service)."""

from maxitor.samples.billing import PaymentGateway
from maxitor.samples.messaging import NotificationGateway, _shared_notifier

__all__ = ["NotificationGateway", "PaymentGateway", "_shared_notifier"]
