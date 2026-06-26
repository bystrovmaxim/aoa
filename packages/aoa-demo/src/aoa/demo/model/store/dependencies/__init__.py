# packages/aoa-demo/src/aoa/demo/model/store/dependencies/__init__.py
"""Wires the store to billing and messaging (like a real service)."""

from aoa.demo.model.billing import PaymentGateway
from aoa.demo.model.messaging import NotificationGateway, _shared_notifier

__all__ = ["NotificationGateway", "PaymentGateway", "_shared_notifier"]
