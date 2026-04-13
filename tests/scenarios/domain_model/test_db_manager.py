# tests/scenarios/domain_model/test_db_manager.py
"""
Minimal database resource manager for tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Minimal BaseResourceManager implementation for use with
``@connection(TestDbManager, key="db")`` on test Actions.

Tests pass a concrete instance via ``connections={"db": mock_db}`` where
``mock_db`` is a mock with the desired behavior. TestDbManager is only
needed as the TYPE for the @connection decorator.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    # In an Action:
    @connection(TestDbManager, key="db", description="Primary database")
    class FullAction(BaseAction[...]): ...

    # In a test:
    mock_db = AsyncMock(spec=TestDbManager)
    result = await bench.run(action, params, rollup=False, connections={"db": mock_db})
"""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.base_resource_manager import BaseResourceManager

from .domains import TestDomain


@meta(description="Test DB manager for connection decorator tests", domain=TestDomain)
class TestDbManager(BaseResourceManager):
    """
    Minimal BaseResourceManager for tests.

    Used as the type in @connection; tests replace it with a mock.
    No real database logic.
    """

    def get_wrapper_class(self) -> type["BaseResourceManager"] | None:
        """No wrapper class is required for this test manager."""
        return None
