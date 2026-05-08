# tests/resources/test_external_service_resource.py
"""
Tests for ExternalServiceResource — typed holder for one external client reference.
"""

from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.external_service import (
    ExternalServiceResource,
    WrapperExternalServiceResource,
)


def test_stores_service_reference() -> None:
    """Constructor keeps the injected client on ``service``."""
    client = object()
    mgr = ExternalServiceResource(client)
    assert mgr.service is client


def test_check_rollup_support_is_false() -> None:
    """External clients do not participate in SQL-style rollup."""
    mgr = ExternalServiceResource(object())
    assert mgr.check_rollup_support() is False


def test_get_wrapper_class_returns_wrapper_type() -> None:
    """Nested actions receive WrapperExternalServiceResource."""
    mgr = ExternalServiceResource(object())
    cls = mgr.get_wrapper_class()
    assert cls is WrapperExternalServiceResource
    assert issubclass(cls, BaseResource)
