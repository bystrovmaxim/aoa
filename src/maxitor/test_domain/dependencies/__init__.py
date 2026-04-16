# src/maxitor/test_domain/dependencies/__init__.py
"""Сервисы-заглушки для рёбер dependency в графе."""

from maxitor.test_domain.dependencies.notification import TestNotificationService
from maxitor.test_domain.dependencies.payment import TestPaymentService

_shared_notifier = TestNotificationService(gateway="shared")

__all__ = ["TestNotificationService", "TestPaymentService", "_shared_notifier"]
