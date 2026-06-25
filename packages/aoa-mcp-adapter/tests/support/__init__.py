# packages/aoa-mcp-adapter/tests/support/__init__.py
"""
Test-support facade for the MCP adapter test suite.

Re-exports every fixture symbol the MCP adapter tests import by name, so the
tests can use a single flat ``from .support import ...`` line:

- ``PingAction`` / ``SimpleAction`` / ``FullAction`` — smoke-test actions
  (:mod:`.domain_model`).
- ``AdminRole`` — application role used in ``UserInfo`` serialization checks
  (:mod:`.domain_model`).
- ``TestDomain`` — generic ``@meta`` domain for a local handler resource stub
  (:mod:`.domain_model`).
- ``EntityProjectionAdapterTestAction`` / ``EntityProjectionParamsMcpTestAction``
  / ``AdapterTestAction`` — schema-backed adapter-fixture actions
  (:mod:`.adapter_fixtures`).

The :mod:`.domain_model` (domains, roles, services, ``SampleEntity``) and the
``GraphJson`` sibling remain available via their submodules for completeness.
"""

from .adapter_fixtures import (
    AdapterTestAction,
    EntityProjectionAdapterTestAction,
    EntityProjectionParamsMcpTestAction,
    GraphJson,
)
from .domain_model import (
    AdminRole,
    FullAction,
    OrdersDomain,
    PingAction,
    SampleEntity,
    SimpleAction,
    SystemDomain,
    TestDomain,
)

__all__ = [
    "AdapterTestAction",
    "AdminRole",
    "EntityProjectionAdapterTestAction",
    "EntityProjectionParamsMcpTestAction",
    "FullAction",
    "GraphJson",
    "OrdersDomain",
    "PingAction",
    "SampleEntity",
    "SimpleAction",
    "SystemDomain",
    "TestDomain",
]
