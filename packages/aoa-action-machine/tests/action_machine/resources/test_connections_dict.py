# tests/resources/test_connections_dict.py
"""
Tests for typing the ``connections`` mapping as ``dict[str, BaseResource]``.

Aspects and ``machine.run(..., connections=...)`` accept a plain dict at runtime;
this module checks that a typical payload type-checks as the shared annotation.
"""

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.resources.base_resource import BaseResource


class _ResourceTestDomain(BaseDomain):
    name = "resource_test"
    description = "Domain for resource-layer tests."


def meta(description: str, domain: type[BaseDomain]):
    """Test-local metadata decorator matching the graph metadata contract."""

    def decorator(cls):
        cls._meta_info = {"description": description, "domain": domain}
        return cls

    return decorator


@meta(description="Connections dict test resource", domain=_ResourceTestDomain)
class DummyResourceManager(BaseResource):
    """Stub resource manager for tests."""

    def get_wrapper_class(self):
        return None


def test_connections_dict_annotation() -> None:
    """A dict with key 'connection' satisfies dict[str, BaseResource]."""
    res = DummyResourceManager()
    conn: dict[str, BaseResource] = {"connection": res}
    assert conn["connection"] is res
