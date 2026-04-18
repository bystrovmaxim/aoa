# src/maxitor/samples/store/dependencies/__init__.py
"""Связь магазина с биллингом и месседжингом (как в реальном сервисе)."""

from maxitor.samples.billing.payment_gateway import PaymentGateway
from maxitor.samples.messaging import NotificationGateway, _shared_notifier

__all__ = ["NotificationGateway", "PaymentGateway", "_shared_notifier"]
