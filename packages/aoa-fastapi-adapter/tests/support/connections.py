# packages/aoa-fastapi-adapter/tests/support/connections.py
"""
Connection fixtures for the FastAPI adapter test suite.

Provides ``DummyResourceManager`` — a stub ``BaseResource`` used as a per-route
connection value (``connections={'key': res}``). The FastAPI adapter tests
assert it both on the route record and as the connections mapping forwarded to
``machine.run`` (positional arg index 3), including via ``PerCallConnection``.
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
