# tests/resources/test_connections_dict.py
"""
Tests for typing the ``connections`` mapping as ``Connections``.

Aspects and ``machine.run(..., connections=...)`` accept a plain dict at runtime;
this module checks that a typical payload type-checks as the shared annotation.
"""

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.resources import BaseController, Connections


class _ResourceTestDomain(BaseDomain):
    name = "resource_test"
    description = "Domain for resource-layer tests."


def meta(description: str):
    """Test-local metadata decorator matching the graph metadata contract (a resource has no domain)."""

    def decorator(cls):
        cls._meta_info = {"description": description, "domain": None}
        return cls

    return decorator


@meta(description="Connections dict test resource")
class DummyController(BaseController):
    """Stub resource manager for tests."""

    @classmethod
    def get_wrapper_class(cls):
        return None


def test_connections_dict_annotation() -> None:
    """A dict with key 'connection' satisfies Connections."""
    res = DummyController()
    conn: Connections = {"connection": res}
    assert conn["connection"] is res
