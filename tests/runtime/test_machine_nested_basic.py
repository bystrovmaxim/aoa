# tests/runtime/test_machine_nested_basic.py
"""Basic nested box.run() and shared-context scenarios for ActionProductMachine."""

from __future__ import annotations

import pytest

from tests.runtime._machine_nested_actions import (
    ChildNestedParams,
    ChildNestedTestAction,
    ParentNestedParams,
    ParentNestedTestAction,
)


class TestBasicNestedCall:
    """Aspect invokes a child action via box.run()."""

    @pytest.mark.asyncio
    async def test_parent_calls_child_and_uses_result(self, machine, context) -> None:
        action = ParentNestedTestAction()
        params = ParentNestedParams()
        result = await machine.run(context, action, params)
        assert result.combined == "parent+from_child"

    @pytest.mark.asyncio
    async def test_child_action_executes_independently(self, machine, context) -> None:
        action = ChildNestedTestAction()
        params = ChildNestedParams()
        result = await machine.run(context, action, params)
        assert result.child_data == "from_child"


class TestContextIsolation:
    """Child run receives the same Context as the parent."""

    @pytest.mark.asyncio
    async def test_child_receives_same_context(self, machine, context) -> None:
        action = ParentNestedTestAction()
        params = ParentNestedParams()
        result = await machine.run(context, action, params)
        assert result.combined == "parent+from_child"
