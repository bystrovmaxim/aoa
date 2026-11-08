# packages/aoa-fastapi-adapter/tests/support/connections.py
"""
Connection fixtures for the FastAPI adapter test suite.

Provides ``DummyController`` — a stub ``BaseResource`` used as a per-route
connection value (``connections={'key': res}``). The FastAPI adapter tests
assert it both on the route record and as the connections mapping forwarded to
``machine.run`` (positional arg index 3), including via ``PerCallConnection``.
"""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseController


@meta(description="Connections dict test resource")
class DummyController(BaseController):
    """Stub resource manager for tests."""

    @classmethod
    def get_wrapper_class(cls):
        return None
