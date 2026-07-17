# packages/aoa-fastapi-adapter/tests/support/__init__.py
"""
Test-support facade for the FastAPI adapter test suite.

Re-exports every fixture symbol the FastAPI adapter tests import by name, so the
tests can use a single flat ``from .support import ...`` line:

- ``PingAction`` / ``SimpleAction`` — smoke-test actions (:mod:`.domain_model`).
- ``DummyResourceManager`` — stub per-route connection (:mod:`.connections`).
- ``EntityProjectionAdapterTestAction`` / ``AdapterTestAction`` — schema-backed
  adapter-fixture actions (:mod:`.adapter_fixtures`).

The :mod:`.domain_model` (domains, ``SampleEntity``) and the ``GraphJson`` /
``EntityProjectionParamsMcpTestAction`` siblings remain available via their
submodules for completeness.
"""

from .adapter_fixtures import (
    AdapterTestAction,
    EntityProjectionAdapterTestAction,
    EntityProjectionParamsMcpTestAction,
    GraphJson,
)
from .connections import DummyResourceManager
from .domain_model import (
    OrdersDomain,
    PingAction,
    SampleEntity,
    SimpleAction,
    SystemDomain,
    TestDomain,
)
from .permissions_fixtures import CancelOrderAction, ManagerRole, UserRole

__all__ = [
    "AdapterTestAction",
    "CancelOrderAction",
    "DummyResourceManager",
    "EntityProjectionAdapterTestAction",
    "EntityProjectionParamsMcpTestAction",
    "GraphJson",
    "ManagerRole",
    "OrdersDomain",
    "PingAction",
    "SampleEntity",
    "SimpleAction",
    "SystemDomain",
    "TestDomain",
    "UserRole",
]
