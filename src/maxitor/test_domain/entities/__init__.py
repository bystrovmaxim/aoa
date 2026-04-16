# src/maxitor/test_domain/entities/__init__.py
"""Тестовые сущности — только для статического графа."""

from maxitor.test_domain.entities.audit_log_entity import TestAuditLogEntity
from maxitor.test_domain.entities.customer_entity import TestCustomerEntity
from maxitor.test_domain.entities.lifecycle import TestOrderLifecycle
from maxitor.test_domain.entities.order_entity import TestOrderEntity
from maxitor.test_domain.entities.order_item_entity import TestOrderItemEntity

TestAuditLogEntity.model_rebuild()

__all__ = [
    "TestAuditLogEntity",
    "TestCustomerEntity",
    "TestOrderEntity",
    "TestOrderItemEntity",
    "TestOrderLifecycle",
]
