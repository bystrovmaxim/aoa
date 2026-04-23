# tests/scenarios/domain_model/test_db_manager.py
"""
Test resource manager class for ``@depends`` / ``@connection`` (same pattern: pass a **class**).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Concrete ``BaseResource`` used as the **type** in decorators, e.g.::

    @depends(TestDbManager, description="…")
    @connection(TestDbManager, key="db", description="…")

That mirrors ``@depends(SomeAction)``: the graph resolves to the canonical
``resource_manager`` vertex for this class (one node shared by depends + connection).

Tests inject instances via ``connections={\"db\": mock}`` and mock ``box.resolve(TestDbManager)``.
"""

from __future__ import annotations

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.base_resource import BaseResource

from .domains import OrdersDomain


@meta(
    description="Test database resource manager for order-scenario actions",
    domain=OrdersDomain,
)
class TestDbManager(BaseResource):
    """Minimal manager; runtime tests use ``AsyncMock(spec=TestDbManager)``."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None
