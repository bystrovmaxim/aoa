# packages/aoa-demo/src/aoa/demo/model/store/dependencies/__init__.py
"""Wires the store to billing and messaging (like a real service)."""

from aoa.demo.model.billing import PaymentClient
from aoa.demo.model.messaging import NotificationClient, _shared_notifier

__all__ = ["NotificationClient", "PaymentClient", "_shared_notifier"]
