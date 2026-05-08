# tests/scenarios/domain_model/test_db_manager.py
"""
Sample ``BaseResource`` for the orders test domain: ``@depends`` / ``@connection`` (class references).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Concrete ``BaseResource`` used as the **type** in decorators, e.g.::

    @depends(OrdersDbManager, description="…")
    @connection(OrdersDbManager, key="db", description="…")

That mirrors ``@depends(SomeAction)``: the graph resolves to the canonical
``resource_manager`` graph node for this class (one node shared by depends + connection).

Tests inject instances via ``connections={\"db\": mock}`` and mock ``box.resolve(OrdersDbManager)``.
"""

from __future__ import annotations

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.base_resource import BaseResource

from .domains import OrdersDomain


@meta(
    description="Test database resource manager for order-scenario actions",
    domain=OrdersDomain,
)
class OrdersDbManager(BaseResource):
    """Minimal manager; runtime tests use ``AsyncMock(spec=OrdersDbManager)``."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None
