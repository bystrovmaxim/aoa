# tests/resources/test_external_service_manager.py
"""
Tests for ExternalServiceManager — typed holder for one external client reference.
"""

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.external_service import (
    ExternalServiceManager,
    WrapperExternalServiceManager,
)


def test_stores_service_reference() -> None:
    """Constructor keeps the injected client on ``service``."""
    client = object()
    mgr = ExternalServiceManager(client)
    assert mgr.service is client


def test_check_rollup_support_is_false() -> None:
    """External clients do not participate in SQL-style rollup."""
    mgr = ExternalServiceManager(object())
    assert mgr.check_rollup_support() is False


def test_get_wrapper_class_returns_wrapper_type() -> None:
    """Nested actions receive WrapperExternalServiceManager."""
    mgr = ExternalServiceManager(object())
    cls = mgr.get_wrapper_class()
    assert cls is WrapperExternalServiceManager
    assert issubclass(cls, BaseResourceManager)
